import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import { Message } from '../../models/message.model';
import { ReasoningTraceComponent } from '../reasoning-trace/reasoning-trace.component';

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
            <p class="whitespace-pre-wrap leading-relaxed">{{ message().text }}</p>
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
  readonly message = input.required<Message>();

  protected readonly isUser = computed(() => this.message().role === 'user');
  protected readonly isSystem = computed(
    () => this.message().role === 'system',
  );

  protected readonly hasTraces = computed(
    () => (this.message().toolCalls?.length ?? 0) > 0,
  );

  protected readonly bubbleClass = computed(() =>
    this.isUser()
      ? 'bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2.5 text-sm'
      : 'bg-slate-100 text-slate-900 rounded-2xl rounded-bl-md px-4 py-2.5 text-sm',
  );
}
