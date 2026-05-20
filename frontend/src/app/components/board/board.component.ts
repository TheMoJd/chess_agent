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
    const fenAfter = this.board.getFEN?.();
    if (!fenAfter || fenAfter === this.lastSyncedFen) return;
    const fenBefore = this.lastSyncedFen;
    this.lastSyncedFen = fenAfter;

    // Castle d'abord : ngx-chess-board renvoie l'UCI "e1g1" même pour un roque,
    // ce qui fait passer le coup pour un coup de roi banal côté agent.
    // On détecte via la diff de FEN (canonique, indépendante de l'orientation).
    const san =
      this.detectCastle(fenBefore, fenAfter) ??
      this.extractSan(event) ??
      this.coordsToFallback(event);
    this.chess.recordMove(san, fenAfter);
    // Plus d'envoi auto : l'user déclenche l'analyse via le bouton dédié.
    // Si une analyse précédente tourne encore, on la cancel — la position a
    // changé, l'avis arriverait obsolète.
    if (this.chat.loading()) {
      this.chat.cancelInFlight();
    }
  }

  /** Détecte un roque en comparant la colonne du roi avant/après le coup.
   *
   * En SAN, "O-O" / "O-O-O" sont les seules notations correctes — l'UCI
   * "e1g1" laisse l'agent croire à un coup de roi normal. Comme le roi est la
   * seule pièce qui peut changer de colonne de ±2 en un coup, la diff de file
   * suffit. On reste sur la FEN (canonique) pour ne pas dépendre du flip
   * visuel du board.
   */
  private detectCastle(
    fenBefore: string,
    fenAfter: string,
  ): 'O-O' | 'O-O-O' | null {
    if (!fenBefore) return null;
    // FEN active-color = qui doit jouer ENSUITE → celui qui vient de jouer
    // est l'opposé. 'w' suivant → noir a joué → on regarde 'k'.
    const sideToMoveNext = fenAfter.split(' ')[1];
    const kingChar: 'K' | 'k' = sideToMoveNext === 'w' ? 'k' : 'K';
    const before = this.kingFile(fenBefore, kingChar);
    const after = this.kingFile(fenAfter, kingChar);
    if (before < 0 || after < 0) return null;
    const delta = after - before;
    if (delta === 2) return 'O-O';
    if (delta === -2) return 'O-O-O';
    return null;
  }

  /** Retourne la colonne (0-7) du roi `kingChar` dans la FEN, -1 si absent. */
  private kingFile(fen: string, kingChar: 'K' | 'k'): number {
    const board = fen.split(' ')[0];
    for (const rank of board.split('/')) {
      let col = 0;
      for (const ch of rank) {
        if (ch === kingChar) return col;
        if (ch >= '1' && ch <= '8') col += +ch;
        else col++;
      }
    }
    return -1;
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
