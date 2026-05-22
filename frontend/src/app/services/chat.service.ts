import { Injectable, computed, inject, signal } from '@angular/core';

import { environment } from '../../environments/environment';
import { ChatRequest, ToolCallTrace } from '../models/chat.model';
import { Message } from '../models/message.model';
import { ChessService, UserColor } from './chess.service';
import { SessionService } from './session.service';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly session = inject(SessionService);
  private readonly chess = inject(ChessService);
  private readonly url = `${environment.apiBaseUrl}/chat/stream`;

  readonly messages = signal<Message[]>([]);
  readonly loading = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  /**
   * moveCount() au moment du dernier "Lancer l'analyse". Si la valeur est
   * inférieure à moveCount() courant, c'est qu'un coup a été joué depuis,
   * donc l'agent n'a pas encore vu la position → le bouton se réactive.
   */
  readonly lastAnalyzedMoveCount = signal<number>(0);

  /**
   * État global du bouton "Lancer l'analyse". Vrai uniquement si :
   * - pas déjà en train de tourner,
   * - au moins un coup a été joué,
   * - et la position courante n'a pas encore été analysée.
   */
  readonly canAnalyze = computed(
    () =>
      !this.loading() &&
      this.chess.moveCount() > 0 &&
      this.chess.moveCount() > this.lastAnalyzedMoveCount(),
  );

  /**
   * AbortController de la requête SSE en vol. `abort()` coupe net le stream
   * (la connexion HTTP est fermée côté client, le backend voit un disconnect
   * et arrête le générateur). Mémorisé pour permettre cancelInFlight().
   */
  private inFlight: AbortController | null = null;

  /**
   * ID du message assistant en cours de streaming. Permet de retrouver la
   * bulle à muter à chaque token sans scan O(n) du tableau messages.
   */
  private streamingMessageId: string | null = null;

  /** Notifie l'agent qu'un coup vient d'être joué sur l'échiquier.
   *
   * Le wording dépend de qui vient de jouer (déduit du FEN APRÈS le coup :
   * le champ "active color" indique qui doit jouer ENSUITE, donc l'opposé
   * de celui qui vient de jouer). Si c'est la couleur du user → "j'ai joué".
   * Sinon → "les blancs/noirs jouent" : l'agent change de posture pédagogique
   * (anticipation/explication adverse vs validation/correction perso).
   */
  sendMove(san: string, fen: string): void {
    const sideToMoveNext = fen.split(' ')[1];
    const playedBy: UserColor = sideToMoveNext === 'w' ? 'black' : 'white';
    const userColor = this.chess.userColor();

    const message =
      playedBy === userColor
        ? `J'ai joué ${san}.`
        : `${playedBy === 'white' ? 'Les blancs' : 'Les noirs'} jouent ${san}.`;

    this.send(message, fen);
  }

  /** Envoie un message libre tapé par l'utilisateur. */
  sendText(text: string, fen: string | null): void {
    const t = text.trim();
    if (!t) return;
    this.send(t, fen);
  }

  /**
   * Déclenche l'analyse du dernier coup joué. Réutilise sendMove() pour le
   * formattage du message (intro de couleur au 1er message + "j'ai joué X" /
   * "les noirs jouent X" selon perspective).
   *
   * Marque `lastAnalyzedMoveCount` à la valeur courante pour désactiver
   * immédiatement le bouton — il se réactivera quand l'user jouera un coup.
   */
  analyzeCurrentPosition(): void {
    const last = this.chess.history().at(-1);
    if (!last) return;
    this.lastAnalyzedMoveCount.set(this.chess.moveCount());
    this.sendMove(last.san, last.fenAfter);
  }

  /**
   * Annule la requête HTTP en vol. Le message user déjà affiché reste, suivi
   * d'une ligne système "Analyse annulée" pour que l'historique reflète
   * fidèlement la réalité (l'user a demandé, puis abandonné).
   *
   * `reason` distingue les deux origines possibles :
   * - 'move' : un coup a été joué pendant l'analyse (déclenché par board.component)
   * - 'user' : l'user a cliqué sur le bouton "Arrêter" du chat-panel
   */
  cancelInFlight(reason: 'move' | 'user' = 'move'): void {
    if (!this.inFlight) return;
    this.inFlight.abort();
    this.inFlight = null;
    this.streamingMessageId = null;
    this.loading.set(false);
    const text =
      reason === 'user'
        ? 'Analyse interrompue.'
        : 'Analyse annulée par un nouveau coup.';
    this.messages.update((m) => [
      ...m,
      {
        id: crypto.randomUUID(),
        role: 'system',
        text,
        timestamp: Date.now(),
      },
    ]);
  }

  /** Informe l'agent que le user a tourné l'échiquier (changement de perspective).
   *
   * À appeler UNIQUEMENT si une conversation est déjà en cours — sinon le
   * préfixe automatique du premier message annoncera déjà la couleur.
   */
  notifyColorChange(): void {
    const color =
      this.chess.userColor() === 'white' ? 'les blancs' : 'les noirs';
    this.send(
      `Je change de perspective, je joue maintenant ${color}.`,
      this.chess.fen(),
    );
  }

  private send(message: string, fen: string | null): void {
    // Au tout premier message d'une session, on annonce la couleur du user
    // pour que l'agent calibre ses conseils dès le départ.
    let finalMessage = message;
    if (this.messages().length === 0) {
      const colorLabel =
        this.chess.userColor() === 'white' ? 'les blancs' : 'les noirs';
      finalMessage = `Je joue ${colorLabel}. ${message}`;
    }

    // Optimistic update : on affiche immédiatement le message user et une
    // bulle assistant VIDE qui se remplira au fil du stream. L'ID de la bulle
    // assistant est mémorisé pour append les tokens sans re-scan.
    const assistantId = crypto.randomUUID();
    this.streamingMessageId = assistantId;
    this.messages.update((m) => [
      ...m,
      {
        id: crypto.randomUUID(),
        role: 'user',
        text: finalMessage,
        timestamp: Date.now(),
      },
      {
        id: assistantId,
        role: 'assistant',
        text: '',
        toolCalls: [],
        timestamp: Date.now(),
      },
    ]);
    this.loading.set(true);
    this.error.set(null);

    const body: ChatRequest = {
      session_id: this.session.sessionId(),
      message: finalMessage,
      fen,
      // Source de vérité côté front pour la couleur courante. Le backend
      // l'injecte dans le HumanMessage sous forme de tag structuré, plus
      // robuste que de faire inférer l'agent depuis la conversation.
      user_color: this.chess.userColor(),
    };

    // Fire-and-forget : l'async function se résout quand le stream est consommé.
    // Pas de await — on rend la main au caller (board ou chat-panel) tout de suite.
    void this.streamRequest(body, assistantId);
  }

  /** Ouvre le stream SSE et applique chaque event au signal messages.
   *
   * Pourquoi pas HttpClient ? Angular's HttpClient ne supporte pas le
   * `responseType: 'stream'`. fetch + ReadableStream est le seul chemin
   * stable pour consommer du SSE avec un POST body en 2026.
   */
  private async streamRequest(body: ChatRequest, assistantId: string): Promise<void> {
    const controller = new AbortController();
    this.inFlight = controller;

    try {
      const resp = await fetch(this.url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // Pump : on lit le stream chunk par chunk. Les bytes peuvent arriver
      // au milieu d'une frame SSE → on accumule jusqu'à voir `\n\n`.
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Découpe en frames SSE (séparées par double newline).
        let separatorIdx: number;
        while ((separatorIdx = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, separatorIdx);
          buffer = buffer.slice(separatorIdx + 2);
          this.handleSseFrame(frame, assistantId);
        }
      }
    } catch (err) {
      // AbortError = annulation volontaire (cancelInFlight) → pas une erreur.
      if (err instanceof DOMException && err.name === 'AbortError') return;
      this.error.set(this.formatError(err));
      this.loading.set(false);
      this.streamingMessageId = null;
    } finally {
      if (this.inFlight === controller) this.inFlight = null;
    }
  }

  /** Parse une frame SSE (`event: ...\ndata: ...`) et dispatch selon le type.
   *
   * Spec SSE : chaque frame contient des lignes `key: value`. On ne gère que
   * `event:` et `data:` — les autres (`id:`, `retry:`) ne sont pas utilisés
   * côté backend. Les commentaires (`:` en début de ligne) sont ignorés.
   */
  private handleSseFrame(frame: string, assistantId: string): void {
    let eventType = 'message';
    let dataLine = '';
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) eventType = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLine += line.slice(5).trim();
    }
    if (!dataLine) return;

    let data: unknown;
    try {
      data = JSON.parse(dataLine);
    } catch {
      return; // frame corrompue, on skip silencieusement
    }

    switch (eventType) {
      case 'token':
        this.appendToken(assistantId, (data as { text: string }).text);
        break;
      case 'tool_start':
        this.appendToolCall(assistantId, data as { id: string; name: string; args: Record<string, unknown> });
        break;
      case 'tool_end':
        this.completeToolCall(assistantId, data as { id: string; result: string });
        break;
      case 'done':
        this.loading.set(false);
        this.streamingMessageId = null;
        break;
      case 'error':
        this.error.set((data as { detail: string }).detail);
        this.loading.set(false);
        this.streamingMessageId = null;
        break;
    }
  }

  /** Append text à la bulle assistant en cours. Mutation immutable du signal. */
  private appendToken(assistantId: string, text: string): void {
    this.messages.update((m) =>
      m.map((msg) =>
        msg.id === assistantId ? { ...msg, text: msg.text + text } : msg,
      ),
    );
  }

  /** Ajoute un tool call (avec result vide) à la bulle assistant.
   *
   * On stocke l'id LangGraph dans args.__id pour matcher le tool_end plus
   * tard — `ToolCallTrace` du backend n'a pas de champ id natif, donc on
   * détourne `args` qui est un dict ouvert.
   */
  private appendToolCall(
    assistantId: string,
    payload: { id: string; name: string; args: Record<string, unknown> },
  ): void {
    const trace: ToolCallTrace & { __id: string } = {
      __id: payload.id,
      name: payload.name,
      args: payload.args,
      result: '',
    };
    this.messages.update((m) =>
      m.map((msg) =>
        msg.id === assistantId
          ? { ...msg, toolCalls: [...(msg.toolCalls ?? []), trace] }
          : msg,
      ),
    );
  }

  /** Remplit le `result` du tool call matchant l'id LangGraph. */
  private completeToolCall(
    assistantId: string,
    payload: { id: string; result: string },
  ): void {
    this.messages.update((m) =>
      m.map((msg) => {
        if (msg.id !== assistantId || !msg.toolCalls) return msg;
        return {
          ...msg,
          toolCalls: msg.toolCalls.map((tc) =>
            (tc as ToolCallTrace & { __id?: string }).__id === payload.id
              ? { ...tc, result: payload.result }
              : tc,
          ),
        };
      }),
    );
  }

  /** Reset l'UI : vide les messages + l'erreur. Ne touche pas au session_id. */
  clear(): void {
    if (this.inFlight) {
      this.inFlight.abort();
      this.inFlight = null;
    }
    this.streamingMessageId = null;
    this.messages.set([]);
    this.error.set(null);
    this.loading.set(false);
    this.lastAnalyzedMoveCount.set(0);
  }

  private formatError(err: unknown): string {
    if (err instanceof TypeError && err.message.includes('fetch')) {
      return "Backend injoignable. Vérifie qu'il tourne sur :8000.";
    }
    if (err instanceof Error) {
      return err.message;
    }
    return 'Erreur inattendue.';
  }
}
