import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { LucideAngularModule, Send } from 'lucide-angular';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [LucideAngularModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form
      (submit)="$event.preventDefault(); send()"
      class="border-t border-slate-200 p-3 flex items-end gap-2 bg-white"
    >
      <textarea
        [value]="text()"
        (input)="text.set(asInput($event).value)"
        (keydown.enter)="onEnter($event)"
        [disabled]="disabled()"
        placeholder="Pose une question ou commente une position…"
        rows="1"
        class="flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm
               focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
               disabled:bg-slate-50 disabled:text-slate-400 max-h-32"
      ></textarea>
      <button
        type="submit"
        [disabled]="!canSend()"
        class="rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-40
               disabled:cursor-not-allowed text-white p-2.5 transition
               focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        aria-label="Envoyer"
      >
        <lucide-icon [img]="sendIcon" class="w-5 h-5"></lucide-icon>
      </button>
    </form>
  `,
})
export class ChatInputComponent {
  readonly disabled = input<boolean>(false);
  readonly sendMessage = output<string>();

  protected readonly text = signal('');
  protected readonly sendIcon = Send;

  protected readonly canSend = computed(
    () => !this.disabled() && this.text().trim().length > 0,
  );

  protected asInput(ev: Event): HTMLTextAreaElement {
    return ev.target as HTMLTextAreaElement;
  }

  protected onEnter(ev: Event): void {
    const keyEv = ev as KeyboardEvent;
    if (keyEv.shiftKey) return; // Shift+Enter = newline
    ev.preventDefault();
    this.send();
  }

  protected send(): void {
    if (!this.canSend()) return;
    this.sendMessage.emit(this.text());
    this.text.set('');
  }
}
