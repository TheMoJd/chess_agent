import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
} from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';

import { Message } from '../../models/message.model';
import { ReasoningTraceComponent } from '../reasoning-trace/reasoning-trace.component';

// Configuration marked : GFM activé pour autoriser tables/listes, breaks pour
// que les \n du LLM deviennent des <br>. Pas de async — on veut un parse
// synchrone pour pouvoir le brancher dans un computed.
marked.setOptions({ gfm: true, breaks: true, async: false });

@Component({
  selector: 'app-message-bubble',
  standalone: true,
  imports: [ReasoningTraceComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (isSystem()) {
      <div class="flex justify-center">
        <span class="text-xs text-slate-500 italic">⚫ {{ message().text }}</span>
      </div>
    } @else {
      <div class="flex" [class.justify-end]="isUser()">
        <div class="max-w-[85%] flex flex-col gap-2" [class.items-end]="isUser()">
          <div [class]="bubbleClass()">
            <!-- User : texte brut (pas de markdown attendu).
                 Assistant : on rend le markdown via [innerHTML].
                 Angular DomSanitizer retire automatiquement scripts/handlers.
                 Si assistant + texte vide (= en attente du 1er token du stream),
                 on affiche un indicateur 3-dots à la place. -->
            @if (isUser()) {
              <p class="whitespace-pre-wrap leading-relaxed">{{ message().text }}</p>
            } @else if (isEmptyAssistant()) {
              <div class="flex items-center gap-1.5 py-1">
                <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse"></span>
                <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse [animation-delay:150ms]"></span>
                <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse [animation-delay:300ms]"></span>
              </div>
            } @else {
              <div class="markdown-content text-sm leading-relaxed"
                   [innerHTML]="renderedMarkdown()"></div>
            }
          </div>
          @if (!isUser() && hasTraces()) {
            <app-reasoning-trace [traces]="message().toolCalls!"></app-reasoning-trace>
          }
        </div>
      </div>
    }
  `,
})
export class MessageBubbleComponent {
  private readonly sanitizer = inject(DomSanitizer);

  readonly message = input.required<Message>();

  protected readonly isUser = computed(() => this.message().role === 'user');
  protected readonly isSystem = computed(
    () => this.message().role === 'system',
  );

  protected readonly hasTraces = computed(
    () => (this.message().toolCalls?.length ?? 0) > 0,
  );

  /** Bulle assistant en attente du 1er token (text vide). Déclenche le placeholder 3-dots. */
  protected readonly isEmptyAssistant = computed(
    () => !this.isUser() && !this.isSystem() && this.message().text === '',
  );

  protected readonly bubbleClass = computed(() =>
    this.isUser()
      ? 'bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2.5 text-sm'
      : 'bg-slate-100 text-slate-900 rounded-2xl rounded-bl-md px-4 py-2.5 text-sm',
  );

  /**
   * Markdown → HTML sanitisé. `bypassSecurityTrustHtml` est OK ici car la source
   * est notre backend (sortie LLM filtrée), pas du contenu user-generated arbitraire.
   */
  protected readonly renderedMarkdown = computed<SafeHtml>(() => {
    const html = marked.parse(this.message().text) as string;
    return this.sanitizer.bypassSecurityTrustHtml(html);
  });
}
