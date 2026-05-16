import { Injectable, signal } from '@angular/core';

/**
 * Gère l'identifiant de session côté front. Persistance localStorage pour
 * survivre aux refreshs. Le backend (LangGraph + AsyncMongoDBSaver) utilise
 * ce session_id comme thread_id pour récupérer l'historique de conversation.
 */
@Injectable({ providedIn: 'root' })
export class SessionService {
  private readonly STORAGE_KEY = 'chess_agent_session_id';
  readonly sessionId = signal<string>(this.loadOrCreate());

  private loadOrCreate(): string {
    if (typeof localStorage === 'undefined') {
      return crypto.randomUUID();
    }
    const cached = localStorage.getItem(this.STORAGE_KEY);
    if (cached) return cached;
    const id = crypto.randomUUID();
    localStorage.setItem(this.STORAGE_KEY, id);
    return id;
  }

  reset(): void {
    const id = crypto.randomUUID();
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(this.STORAGE_KEY, id);
    }
    this.sessionId.set(id);
  }
}
