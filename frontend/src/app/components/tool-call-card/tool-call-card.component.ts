import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  signal,
} from '@angular/core';
import { ChevronDown, ChevronUp, LucideAngularModule } from 'lucide-angular';

import { ToolCallTrace } from '../../models/chat.model';
import { getToolMeta } from '../../models/tool-meta';

@Component({
  selector: 'app-tool-call-card',
  standalone: true,
  imports: [LucideAngularModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="rounded-lg border border-slate-200 overflow-hidden">
      <div class="flex items-center gap-2 px-3 py-2" [class]="meta().bgClass">
        <lucide-icon
          [img]="meta().icon"
          class="w-3.5 h-3.5"
          [class]="meta().textClass"
        ></lucide-icon>
        <span class="text-xs font-semibold" [class]="meta().textClass">
          {{ meta().label }}
        </span>
      </div>

      <div class="px-3 py-2 space-y-2 bg-white">
        @if (hasArgs()) {
          <div>
            <span class="text-[10px] uppercase tracking-wide text-slate-500 font-semibold">
              Arguments
            </span>
            <pre
              class="mt-1 text-xs font-mono text-slate-700 bg-slate-50 rounded p-2 overflow-x-auto whitespace-pre-wrap break-words"
            >{{ argsFormatted() }}</pre>
          </div>
        }

        <button
          type="button"
          (click)="expanded.update(v => !v)"
          class="text-xs font-medium text-slate-600 hover:text-slate-900 transition flex items-center gap-1
                 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
        >
          <lucide-icon
            [img]="expanded() ? chevronUpIcon : chevronDownIcon"
            class="w-3 h-3"
          ></lucide-icon>
          {{ expanded() ? 'Cacher' : 'Voir' }} le résultat
        </button>

        @if (expanded()) {
          <pre
            class="text-xs font-mono text-slate-700 bg-slate-50 rounded p-2 overflow-x-auto whitespace-pre-wrap break-words max-h-64 overflow-y-auto"
          >{{ resultFormatted() }}</pre>
        }
      </div>
    </div>
  `,
})
export class ToolCallCardComponent {
  readonly trace = input.required<ToolCallTrace>();

  protected readonly expanded = signal(false);
  protected readonly chevronUpIcon = ChevronUp;
  protected readonly chevronDownIcon = ChevronDown;

  protected readonly meta = computed(() => getToolMeta(this.trace().name));

  protected readonly hasArgs = computed(
    () => Object.keys(this.trace().args ?? {}).length > 0,
  );

  protected readonly argsFormatted = computed(() =>
    JSON.stringify(this.trace().args, null, 2),
  );

  protected readonly resultFormatted = computed(() => {
    const raw = this.trace().result;
    if (!raw) return '(vide)';
    try {
      return JSON.stringify(JSON.parse(raw), null, 2);
    } catch {
      return raw;
    }
  });
}
