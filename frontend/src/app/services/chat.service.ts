import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Subscription, timeout } from 'rxjs';

import { environment } from '../../environments/environment';
import { ChatRequest, ChatResponse } from '../models/chat.model';
import { Message } from '../models/message.model';
import { ChessService, UserColor } from './chess.service';
import { SessionService } from './session.service';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly http = inject(HttpClient);
  private readonly session = inject(SessionService);
  private readonly chess = inject(ChessService);
  private readonly url = `${environment.apiBaseUrl}/chat`;

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
   * Subscription HTTP en vol. Mémorisée pour pouvoir l'annuler explicitement
   * via cancelInFlight() (cf. board.component.ts : si l'user joue pendant
   * qu'une analyse tourne, on cancel pour ne pas recevoir un avis obsolète).
   */
  private inFlight: Subscription | null = null;

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
   */
  cancelInFlight(): void {
    if (!this.inFlight) return;
    this.inFlight.unsubscribe();
    this.inFlight = null;
    this.loading.set(false);
    this.messages.update((m) => [
      ...m,
      {
        id: crypto.randomUUID(),
        role: 'system',
        text: 'Analyse annulée par un nouveau coup.',
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

    // Optimistic update : on affiche immédiatement le message user.
    this.messages.update((m) => [
      ...m,
      {
        id: crypto.randomUUID(),
        role: 'user',
        text: finalMessage,
        timestamp: Date.now(),
      },
    ]);
    this.loading.set(true);
    this.error.set(null);

    const body: ChatRequest = {
      session_id: this.session.sessionId(),
      message: finalMessage,
      fen,
    };

    this.inFlight = this.http
      .post<ChatResponse>(this.url, body)
      .pipe(timeout(60_000))
      .subscribe({
        next: (resp) => {
          this.messages.update((m) => [
            ...m,
            {
              id: crypto.randomUUID(),
              role: 'assistant',
              text: resp.reply,
              toolCalls: resp.tool_calls,
              timestamp: Date.now(),
            },
          ]);
          this.loading.set(false);
          this.inFlight = null;
        },
        error: (err) => {
          this.error.set(this.formatError(err));
          this.loading.set(false);
          this.inFlight = null;
        },
      });
  }

  /** Reset l'UI : vide les messages + l'erreur. Ne touche pas au session_id. */
  clear(): void {
    if (this.inFlight) {
      this.inFlight.unsubscribe();
      this.inFlight = null;
    }
    this.messages.set([]);
    this.error.set(null);
    this.loading.set(false);
    this.lastAnalyzedMoveCount.set(0);
  }

  private formatError(err: unknown): string {
    if (err instanceof HttpErrorResponse) {
      if (err.status === 0) {
        return "Backend injoignable. Vérifie qu'il tourne sur :8000.";
      }
      if (err.status >= 500) {
        return `Erreur serveur (${err.status}). Réessaie dans un instant.`;
      }
      const detail = (err.error as { detail?: string } | null)?.detail;
      return `Erreur ${err.status}${detail ? ` : ${detail}` : ''}`;
    }
    if (err instanceof Error && err.name === 'TimeoutError') {
      return 'Délai dépassé (60s). Le backend met trop de temps à répondre.';
    }
    return 'Erreur inattendue.';
  }
}
