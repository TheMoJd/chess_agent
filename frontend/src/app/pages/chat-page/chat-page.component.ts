import { ChangeDetectionStrategy, Component, OnInit, inject } from '@angular/core';

import { BoardComponent } from '../../components/board/board.component';
import { BoardControlsComponent } from '../../components/board-controls/board-controls.component';
import { ChatPanelComponent } from '../../components/chat-panel/chat-panel.component';
import { HeaderComponent } from '../../components/header/header.component';
import { AuthService } from '../../services/auth.service';

/**
 * Page principale : layout chess.com-like (board à gauche, chat à droite).
 *
 * Anciennement directement dans App, déplacée ici pour libérer App qui ne fait
 * plus que `<router-outlet>`. La structure interne (header + section + aside)
 * reste identique pour ne pas casser le rendu existant.
 *
 * Au ngOnInit, on appelle refreshMe() pour synchroniser le compteur de quota
 * avec le serveur : le user public en localStorage peut être périmé (ex : un
 * autre onglet a consommé entre-temps).
 */
@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [
    BoardComponent,
    BoardControlsComponent,
    ChatPanelComponent,
    HeaderComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="h-dvh w-screen flex flex-col overflow-hidden">
      <app-header></app-header>
      <main
        class="flex-1 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_440px] gap-4 p-4 overflow-hidden"
      >
        <section
          class="flex flex-col items-center justify-start gap-4 min-h-0 overflow-y-auto py-2"
        >
          <app-board class="w-full max-w-[640px]"></app-board>
          <app-board-controls></app-board-controls>
        </section>

        <aside
          class="bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col overflow-hidden min-h-0"
        >
          <app-chat-panel class="flex-1 min-h-0"></app-chat-panel>
        </aside>
      </main>
    </div>
  `,
})
export class ChatPageComponent implements OnInit {
  private readonly auth = inject(AuthService);

  ngOnInit(): void {
    // Synchro initiale du quota : si le user vient d'un refresh navigateur
    // ou d'un autre onglet, le messages_used en localStorage peut être obsolète.
    // Le subscribe est noop : on s'appuie sur le tap interne qui met à jour
    // currentUser signal. Pas d'unsubscribe nécessaire (HttpClient complete).
    this.auth.refreshMe().subscribe({
      // Silencieux : si /me échoue (401), l'intercepteur logout déjà.
      error: () => {},
    });
  }
}
