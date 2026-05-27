import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { LogOut, LucideAngularModule } from 'lucide-angular';

import { AuthService } from '../../services/auth.service';

/**
 * Header global de la chat-page : logo + email + badge quota + bouton logout.
 *
 * Le badge change de couleur selon le rapport messages_used / quota :
 * - vert tant qu'il reste plus de 20% du quota,
 * - ambre entre 20% et 100%,
 * - rouge à 100% (quota épuisé).
 * Aide visuelle : l'utilisateur sait qu'il doit ralentir avant de bloquer.
 */
@Component({
  selector: 'app-header',
  standalone: true,
  imports: [LucideAngularModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header
      class="w-full flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200"
    >
      <div class="flex items-center gap-3">
        <img
          src="logo.png"
          alt="Chess Agent"
          class="w-10 h-10 object-contain"
          width="40"
          height="40"
        />
        <div class="flex flex-col leading-tight">
          <h1 class="text-lg font-bold tracking-tight text-slate-900">Chess Agent</h1>
          <span class="text-xs text-slate-500">FFE · Tuteur d'ouvertures</span>
        </div>
      </div>

      @if (user(); as u) {
        <div class="flex items-center gap-3">
          <span class="text-sm text-slate-600 hidden sm:inline">{{ u.email }}</span>
          <span
            class="px-2.5 py-1 rounded-full text-xs font-semibold border"
            [class]="quotaBadgeClass()"
            [title]="'Messages consommés ' + u.messages_used + ' / ' + u.quota"
          >
            {{ u.messages_used }} / {{ u.quota }}
          </span>
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-sm font-medium text-slate-700
                   bg-white border border-slate-200 hover:bg-slate-50 transition
                   flex items-center gap-1.5
                   focus:outline-none focus:ring-2 focus:ring-blue-500"
            (click)="logout()"
          >
            <lucide-icon [img]="logoutIcon" class="w-4 h-4"></lucide-icon>
            Déconnexion
          </button>
        </div>
      }
    </header>
  `,
})
export class HeaderComponent {
  private readonly auth = inject(AuthService);
  protected readonly logoutIcon = LogOut;

  protected readonly user = this.auth.currentUser;

  /** Classes Tailwind du badge quota selon le taux d'utilisation. */
  protected readonly quotaBadgeClass = computed(() => {
    const u = this.user();
    if (!u) return 'bg-slate-100 text-slate-600 border-slate-200';
    const ratio = u.quota > 0 ? u.messages_used / u.quota : 1;
    if (ratio >= 1) return 'bg-rose-100 text-rose-800 border-rose-200';
    if (ratio >= 0.8) return 'bg-amber-100 text-amber-800 border-amber-200';
    return 'bg-emerald-100 text-emerald-800 border-emerald-200';
  });

  logout(): void {
    this.auth.logout();
  }
}
