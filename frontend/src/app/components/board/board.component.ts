import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
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
  // detectChanges() cible la subtree de ce composant (board + ngx-chess-board)
  // — bien plus rapide qu'un appRef.tick() qui re-CD tout le chat-panel inutilement.
  private readonly cdr = inject(ChangeDetectorRef);

  @ViewChild('board', { static: true }) board!: NgxChessBoardView;
  // Accès au DOM de <ngx-chess-board> pour toggler la classe anti-animation
  // pendant un flip (cf. flipBoardInstant).
  @ViewChild('board', { read: ElementRef, static: true })
  boardHost!: ElementRef<HTMLElement>;

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
        // La mutation DOM est différée pour ne pas CD pendant la phase en cours.
        const needsReverse = desiredColor === 'black';
        this.currentOrientation = desiredColor;
        queueMicrotask(() => {
          this.board.reset();
          if (needsReverse) this.flipBoardInstant();
          else this.cdr.detectChanges();
        });
      } else {
        queueMicrotask(() => {
          this.board.setFEN(desiredFen);
          this.cdr.detectChanges();
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
      // detectChanges() imbriqué dans la CD déclenche NG0101.
      this.currentOrientation = desired;
      queueMicrotask(() => this.flipBoardInstant());
    });
  }

  /** Reverse + CD en supprimant l'animation CSS pendant l'opération.
   *
   * ngx-chess-board s'appuie sur CDK Drag qui pose une transition
   * `transform .2s` sur chaque pièce. Sur un flip, les 32 pièces animent en
   * parallèle → effet lent. On toggle .no-flip-anim le temps d'un frame
   * pour court-circuiter la transition, puis on la rétablit (on garde
   * l'anim douce pour les déplacements normaux d'une seule pièce). */
  private flipBoardInstant(): void {
    const host = this.boardHost?.nativeElement;
    host?.classList.add('no-flip-anim');
    this.board.reverse();
    this.cdr.detectChanges();
    requestAnimationFrame(() => host?.classList.remove('no-flip-anim'));
  }

  onMove(event: MoveChangeEvent | unknown): void {
    if (!this.board) return;
    const fen = this.board.getFEN?.();
    if (!fen || fen === this.lastSyncedFen) return;
    this.lastSyncedFen = fen;

    const san = this.extractSan(event) ?? this.coordsToFallback(event);
    this.chess.recordMove(san, fen);
    // Plus d'envoi auto : l'user déclenche l'analyse via le bouton dédié.
    // Si une analyse précédente tourne encore, on la cancel — la position a
    // changé, l'avis arriverait obsolète.
    if (this.chat.loading()) {
      this.chat.cancelInFlight();
    }
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
