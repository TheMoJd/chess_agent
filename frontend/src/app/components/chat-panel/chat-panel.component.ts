import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  ViewChild,
  effect,
  inject,
} from '@angular/core';
import { Bot, LucideAngularModule } from 'lucide-angular';

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
        @if (chat.loading()) {
          <div class="flex items-center gap-2 px-4 py-3 rounded-2xl bg-slate-100 w-fit">
            <span class="w-2 h-2 rounded-full bg-slate-400 animate-pulse"></span>
            <span
              class="w-2 h-2 rounded-full bg-slate-400 animate-pulse [animation-delay:150ms]"
            ></span>
            <span
              class="w-2 h-2 rounded-full bg-slate-400 animate-pulse [animation-delay:300ms]"
            ></span>
          </div>
        }
        @if (chat.error()) {
          <div
            class="px-4 py-3 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800"
          >
            {{ chat.error() }}
          </div>
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
