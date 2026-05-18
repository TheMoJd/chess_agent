import {
  ApplicationRef,
  ChangeDetectionStrategy,
  Component,
  ViewChild,
  effect,
  inject,
  signal,
} from '@angular/core';
import { NgxChessBoardModule, NgxChessBoardView } from 'ngx-chess-board';

import { ChatService } from '../../services/chat.service';
import { ChessService } from '../../services/chess.service';

interface MoveChangeEvent {
  move?: string;
  freeMode?: boolean;
  check?: boolean;
  checkmate?: boolean;
  stalemate?: boolean;
  promotion?: string;
  fen?: string;
}

/**
 * Wrapper autour de ngx-chess-board.
 *
 * Responsabilités :
 * 1. Émet les coups joués vers ChessService et ChatService.
 * 2. Synchronise visuellement le board quand le FEN externe change
 *    (cas du undo/reset déclenché ailleurs).
 *
 * Anti-boucle critique : `lastSyncedFen` mémorise la dernière FEN poussée
 * vers/reçue du board, pour éviter setFEN → moveChange → recordMove infini.
 */
@Component({
  selector: 'app-board',
  standalone: true,
  imports: [NgxChessBoardModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex items-center justify-center w-full">
      <ngx-chess-board
        #board
        [size]="size()"
        [lightTileColor]="'#f1f5f9'"
        [darkTileColor]="'#475569'"
        [showCoords]="true"
        (moveChange)="onMove($event)"
      ></ngx-chess-board>
    </div>
  `,
})
export class BoardComponent {
  private readonly chess = inject(ChessService);
  private readonly chat = inject(ChatService);
  // ngx-chess-board mute son state in-place (piece.point.row/col) sans appeler
  // markForCheck. Quand reverse() est invoqué depuis un signal effect, Angular
  // ne déclenche pas forcément de CD sur cette lib zone-based → on force tick().
  private readonly appRef = inject(ApplicationRef);

  @ViewChild('board', { static: true }) board!: NgxChessBoardView;

  // Taille fixe — la responsivité est gérée par le conteneur parent (CSS).
  readonly size = signal(560);

  private lastSyncedFen = '';
  // ngx-chess-board n'expose pas l'orientation courante — on la track nous-même.
  // Default white car le board démarre toujours blancs en bas.
  private currentOrientation: 'white' | 'black' = 'white';

  constructor() {
    // Sync vers le board quand un undo/reset change la FEN à l'extérieur.
    effect(() => {
      const desiredFen = this.chess.fen();
      const desiredColor = this.chess.userColor();
      if (!this.board) return;
      const boardFen = this.board.getFEN?.();
      if (boardFen === desiredFen) return;
      this.lastSyncedFen = desiredFen;
      if (this.chess.moveCount() === 0) {
        // Mirror mis à jour de façon synchrone pour bloquer toute ré-entrée.
        // La mutation DOM est différée pour ne pas tick() pendant la CD en cours.
        const needsReverse = desiredColor === 'black';
        this.currentOrientation = desiredColor;
        queueMicrotask(() => {
          this.board.reset();
          if (needsReverse) this.board.reverse();
          this.appRef.tick();
        });
      } else {
        queueMicrotask(() => {
          this.board.setFEN(desiredFen);
          this.appRef.tick();
        });
      }
    });

    // Sync orientation visuelle ↔ userColor. ngx-chess-board.reverse() est
    // imperatif (toggle), donc on garde un mirror local et on l'appelle
    // seulement quand il y a une vraie divergence.
    effect(() => {
      const desired = this.chess.userColor();
      if (!this.board) return;
      if (this.currentOrientation === desired) return;
      // Update du mirror en synchrone pour éviter une double-bascule si l'effect
      // re-fire avant que le microtask ait tourné. La mutation board.reverse()
      // est queue-microtaskée pour sortir du cycle de CD courant — sinon
      // appRef.tick() imbriqué dans la CD déclenche NG0101.
      this.currentOrientation = desired;
      queueMicrotask(() => {
        this.board.reverse();
        this.appRef.tick();
      });
    });
  }

  onMove(event: MoveChangeEvent | unknown): void {
    if (!this.board) return;
    const fen = this.board.getFEN?.();
    if (!fen || fen === this.lastSyncedFen) return;
    this.lastSyncedFen = fen;

    const san = this.extractSan(event) ?? this.coordsToFallback(event);
    this.chess.recordMove(san, fen);
    this.chat.sendMove(san, fen);
  }

  /** Récupère le SAN du dernier coup via l'historique du board. */
  private extractSan(event: unknown): string | null {
    try {
      const history = this.board.getMoveHistory?.() as unknown as
        | Array<Record<string, unknown>>
        | undefined;
      const last = history?.at(-1);
      const san =
        (last?.['shortMove'] as string | undefined) ??
        (last?.['move'] as string | undefined) ??
        (last?.['san'] as string | undefined);
      if (san) return san;
    } catch {
      // ignore — fallback ci-dessous
    }
    return null;
  }

  /** En dernier recours, log le format des coordonnées (ex: 'e2e4'). */
  private coordsToFallback(event: unknown): string {
    const e = event as MoveChangeEvent | null;
    return e?.move ?? '?';
  }
}
