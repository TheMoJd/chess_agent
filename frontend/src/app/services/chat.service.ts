import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { timeout } from 'rxjs';

import { environment } from '../../environments/environment';
import { ChatRequest, ChatResponse } from '../models/chat.model';
import { Message } from '../models/message.model';
import { SessionService } from './session.service';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly http = inject(HttpClient);
  private readonly session = inject(SessionService);
  private readonly url = `${environment.apiBaseUrl}/chat`;

  readonly messages = signal<Message[]>([]);
  readonly loading = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  /** Notifie l'agent qu'un coup vient d'être joué sur l'échiquier. */
  sendMove(san: string, fen: string): void {
    this.send(`J'ai joué ${san}.`, fen);
  }

  /** Envoie un message libre tapé par l'utilisateur. */
  sendText(text: string, fen: string | null): void {
    const t = text.trim();
    if (!t) return;
    this.send(t, fen);
  }

  private send(message: string, fen: string | null): void {
    // Optimistic update : on affiche immédiatement le message user.
    this.messages.update((m) => [
      ...m,
      {
        id: crypto.randomUUID(),
        role: 'user',
        text: message,
        timestamp: Date.now(),
      },
    ]);
    this.loading.set(true);
    this.error.set(null);

    const body: ChatRequest = {
      session_id: this.session.sessionId(),
      message,
      fen,
    };

    this.http
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
        },
        error: (err) => {
          this.error.set(this.formatError(err));
          this.loading.set(false);
        },
      });
  }

  /** Reset l'UI : vide les messages + l'erreur. Ne touche pas au session_id. */
  clear(): void {
    this.messages.set([]);
    this.error.set(null);
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
