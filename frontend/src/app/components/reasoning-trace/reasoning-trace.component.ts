import {
  ChangeDetectionStrategy,
  Component,
  input,
  signal,
} from '@angular/core';
import {
  Brain,
  ChevronDown,
  ChevronUp,
  LucideAngularModule,
} from 'lucide-angular';

import { ToolCallTrace } from '../../models/chat.model';
import { ToolCallCardComponent } from '../tool-call-card/tool-call-card.component';

@Component({
  selector: 'app-reasoning-trace',
  standalone: true,
  imports: [LucideAngularModule, ToolCallCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="border border-slate-200 rounded-xl bg-white overflow-hidden">
      <button
        type="button"
        (click)="expanded.update(v => !v)"
        class="w-full px-3 py-2 flex items-center justify-between text-xs font-medium text-slate-600 hover:bg-slate-50 transition
               focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <span class="flex items-center gap-2">
          <lucide-icon [img]="brainIcon" class="w-3.5 h-3.5"></lucide-icon>
          Raisonnement ({{ traces().length }} outil{{ traces().length > 1 ? 's' : '' }})
        </span>
        <lucide-icon
          [img]="expanded() ? chevronUpIcon : chevronDownIcon"
          class="w-3.5 h-3.5"
        ></lucide-icon>
      </button>

      @if (expanded()) {
        <div class="border-t border-slate-200 p-2 space-y-2">
          @for (trace of traces(); track $index) {
            <app-tool-call-card [trace]="trace"></app-tool-call-card>
          }
        </div>
      }
    </div>
  `,
})
export class ReasoningTraceComponent {
  readonly traces = input.required<ToolCallTrace[]>();

  // Ouvert par défaut → c'est LE wow factor du POC, on le montre tout de suite.
  protected readonly expanded = signal(true);
  protected readonly brainIcon = Brain;
  protected readonly chevronUpIcon = ChevronUp;
  protected readonly chevronDownIcon = ChevronDown;
}
