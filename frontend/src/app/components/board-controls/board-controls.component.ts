import {
  ChangeDetectionStrategy,
  Component,
  inject,
} from '@angular/core';
import {
  ArrowUpDown,
  LucideAngularModule,
  RotateCcw,
  Undo2,
} from 'lucide-angular';

import { ChatService } from '../../services/chat.service';
import { ChessService } from '../../services/chess.service';
import { SessionService } from '../../services/session.service';

@Component({
  selector: 'app-board-controls',
  standalone: true,
  imports: [LucideAngularModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex gap-2 flex-wrap items-center justify-center">
      <button
        type="button"
        class="px-4 py-2 rounded-lg bg-white border border-slate-200 hover:bg-slate-50
               disabled:opacity-40 disabled:cursor-not-allowed transition
               text-sm font-medium text-slate-700 flex items-center gap-2
               focus:outline-none focus:ring-2 focus:ring-blue-500"
        [disabled]="!chess.canUndo()"
        (click)="undo()"
      >
        <lucide-icon [img]="undoIcon" class="w-4 h-4"></lucide-icon>
        Retour
      </button>
      <button
        type="button"
        class="px-4 py-2 rounded-lg bg-white border border-slate-200 hover:bg-slate-50
               transition text-sm font-medium text-slate-700 flex items-center gap-2
               focus:outline-none focus:ring-2 focus:ring-blue-500"
        [title]="chess.userColor() === 'white' ? 'Jouer les noirs' : 'Jouer les blancs'"
        (click)="flip()"
      >
        <lucide-icon [img]="flipIcon" class="w-4 h-4"></lucide-icon>
        {{ chess.userColor() === 'white' ? 'Jouer noirs' : 'Jouer blancs' }}
      </button>
      <button
        type="button"
        class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white
               text-sm font-medium flex items-center gap-2 transition
               focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        (click)="reset()"
      >
        <lucide-icon [img]="resetIcon" class="w-4 h-4"></lucide-icon>
        Nouvelle partie
      </button>
    </div>
  `,
})
export class BoardControlsComponent {
  protected readonly chess = inject(ChessService);
  private readonly chat = inject(ChatService);
  private readonly session = inject(SessionService);

  protected readonly undoIcon = Undo2;
  protected readonly resetIcon = RotateCcw;
  protected readonly flipIcon = ArrowUpDown;

  undo(): void {
    this.chess.undo();
    // Pas d'appel /chat : on n'informe pas l'agent du undo (décision MVP).
  }

  flip(): void {
    this.chess.toggleUserColor();
    // Si la conversation est déjà entamée, on prévient l'agent du changement
    // de perspective. Sinon le préfixe auto du 1er message s'en chargera.
    if (this.chat.messages().length > 0) {
      this.chat.notifyColorChange();
    }
  }

  reset(): void {
    this.chess.reset();
    this.chat.clear();
    this.session.reset();
  }
}
