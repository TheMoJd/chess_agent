import { computed, Injectable, signal } from '@angular/core';

export interface MoveRecord {
  san: string;
  fenAfter: string;
}

export type UserColor = 'white' | 'black';

const COLOR_STORAGE_KEY = 'chess_agent_user_color';

/**
 * État du jeu côté front.
 *
 * On NE duplique PAS la logique d'échecs : ngx-chess-board valide les coups
 * en interne (via chess.js). On ne stocke que l'historique pour undo et la
 * FEN courante pour passer à l'agent.
 *
 * `userColor` représente la couleur que l'utilisateur a choisi d'apprendre.
 * Elle n'empêche pas de jouer les deux côtés sur l'échiquier (pas de bot dans
 * le MVP) — elle sert uniquement à orienter visuellement le board et à
 * formuler les messages envoyés à l'agent ("j'ai joué X" vs "les noirs jouent X").
 * Persistée en localStorage pour survivre aux refreshs et aux nouvelles parties.
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

  readonly userColor = signal<UserColor>(this.loadUserColor());
  readonly isFlipped = computed(() => this.userColor() === 'black');

  recordMove(san: string, fenAfter: string): void {
    this.history.update((h) => [...h, { san, fenAfter }]);
  }

  undo(): void {
    this.history.update((h) => h.slice(0, -1));
  }

  reset(): void {
    this.history.set([]);
  }

  toggleUserColor(): UserColor {
    const next: UserColor = this.userColor() === 'white' ? 'black' : 'white';
    this.userColor.set(next);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(COLOR_STORAGE_KEY, next);
    }
    return next;
  }

  private loadUserColor(): UserColor {
    if (typeof localStorage === 'undefined') return 'white';
    return localStorage.getItem(COLOR_STORAGE_KEY) === 'black'
      ? 'black'
      : 'white';
  }
}
