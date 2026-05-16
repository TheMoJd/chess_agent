import { ChangeDetectionStrategy, Component } from '@angular/core';
import { LucideAngularModule, MessageCircle } from 'lucide-angular';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [LucideAngularModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex flex-col items-center justify-center text-center py-12 px-6 space-y-3">
      <div
        class="w-14 h-14 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center"
      >
        <lucide-icon [img]="icon" class="w-7 h-7"></lucide-icon>
      </div>
      <h3 class="text-base font-semibold text-slate-900">Salut !</h3>
      <p class="text-sm text-slate-600 max-w-xs leading-relaxed">
        Joue un coup sur l'échiquier ou pose-moi une question.
        Je t'aiderai à comprendre l'ouverture en cours.
      </p>
    </div>
  `,
})
export class EmptyStateComponent {
  protected readonly icon = MessageCircle;
}
