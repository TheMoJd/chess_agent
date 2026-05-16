import { computed, Injectable, signal } from '@angular/core';

export interface MoveRecord {
  san: string;
  fenAfter: string;
}

/**
 * État du jeu côté front.
 *
 * On NE duplique PAS la logique d'échecs : ngx-chess-board valide les coups
 * en interne (via chess.js). On ne stocke que l'historique pour undo et la
 * FEN courante pour passer à l'agent.
 */
@Injectable({ providedIn: 'root' })
export class ChessService {
  private readonly INITIAL_FEN =
    'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

  readonly history = signal<MoveRecord[]>([]);
  readonly fen = computed(
    () => this.history().at(-1)?.fenAfter ?? this.INITIAL_FEN,
  );
  readonly canUndo = computed(() => this.history().length > 0);
  readonly moveCount = computed(() => this.history().length);

  recordMove(san: string, fenAfter: string): void {
    this.history.update((h) => [...h, { san, fenAfter }]);
  }

  undo(): void {
    this.history.update((h) => h.slice(0, -1));
  }

  reset(): void {
    this.history.set([]);
  }
}
