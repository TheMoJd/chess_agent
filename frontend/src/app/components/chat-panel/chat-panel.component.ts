import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  ViewChild,
  effect,
  inject,
} from '@angular/core';
import { Bot, LucideAngularModule, Sparkles, Square } from 'lucide-angular';

import { ChatService } from '../../services/chat.service';
import { ChessService } from '../../services/chess.service';
import { ChatInputComponent } from '../chat-input/chat-input.component';
import { EmptyStateComponent } from '../empty-state/empty-state.component';
import { MessageBubbleComponent } from '../message-bubble/message-bubble.component';

@Component({
  selector: 'app-chat-panel',
  standalone: true,
  imports: [
    ChatInputComponent,
    EmptyStateComponent,
    LucideAngularModule,
    MessageBubbleComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex flex-col h-full">
      <header class="px-5 py-4 border-b border-slate-200 flex items-center gap-3">
        <div
          class="w-9 h-9 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center"
        >
          <lucide-icon [img]="botIcon" class="w-5 h-5"></lucide-icon>
        </div>
        <div>
          <h2 class="text-base font-semibold text-slate-900">Agent FFE</h2>
          <p class="text-xs text-slate-500">Tuteur d'ouvertures</p>
        </div>
      </header>

      <div #scrollContainer class="flex-1 overflow-y-auto px-5 py-4 space-y-3 min-h-0">
        @if (chat.messages().length === 0 && !chat.loading()) {
          <app-empty-state></app-empty-state>
        }
        @for (msg of chat.messages(); track msg.id) {
          <app-message-bubble [message]="msg"></app-message-bubble>
        }
        @if (chat.error()) {
          <div
            class="px-4 py-3 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800"
          >
            {{ chat.error() }}
          </div>
        }
      </div>

      <div class="px-3 py-2 border-t border-slate-100 bg-slate-50">
        @if (chat.loading()) {
          <button
            type="button"
            class="w-full px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white
                   transition text-sm font-medium flex items-center justify-center gap-2
                   focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-2"
            (click)="chat.cancelInFlight('user')"
          >
            <lucide-icon [img]="stopIcon" class="w-4 h-4"></lucide-icon>
            Arrêter l'analyse
          </button>
        } @else {
          <button
            type="button"
            class="w-full px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white
                   disabled:bg-slate-300 disabled:cursor-not-allowed transition
                   text-sm font-medium flex items-center justify-center gap-2
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            [disabled]="!chat.canAnalyze()"
            (click)="chat.analyzeCurrentPosition()"
          >
            <lucide-icon [img]="sparklesIcon" class="w-4 h-4"></lucide-icon>
            Lancer l'analyse
          </button>
        }
      </div>

      <app-chat-input
        [disabled]="chat.loading()"
        (sendMessage)="onSend($event)"
      ></app-chat-input>
    </div>
  `,
})
export class ChatPanelComponent implements AfterViewInit {
  protected readonly chat = inject(ChatService);
  private readonly chess = inject(ChessService);
  protected readonly botIcon = Bot;
  protected readonly sparklesIcon = Sparkles;
  protected readonly stopIcon = Square;

  @ViewChild('scrollContainer', { static: true })
  private scrollContainer!: ElementRef<HTMLDivElement>;

  /** Si l'utilisateur a remonté la conversation manuellement, on évite le scroll auto. */
  private isAtBottom = true;

  constructor() {
    // Auto-scroll quand un nouveau message ou loading change (uniquement si déjà en bas).
    effect(() => {
      // Dépendances : chat.messages() et chat.loading()
      this.chat.messages();
      this.chat.loading();
      if (this.isAtBottom) {
        queueMicrotask(() => this.scrollToBottom());
      }
    });
  }

  ngAfterViewInit(): void {
    const el = this.scrollContainer.nativeElement;
    el.addEventListener('scroll', () => {
      const threshold = 40; // px de marge pour considérer "en bas"
      this.isAtBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    });
  }

  onSend(text: string): void {
    this.chat.sendText(text, this.chess.fen());
  }

  private scrollToBottom(): void {
    const el = this.scrollContainer?.nativeElement;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }
}
