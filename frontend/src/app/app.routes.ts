import { Routes } from '@angular/router';

import { authGuard } from './guards/auth.guard';

/**
 * Routing principal.
 *
 * - /login, /signup : pages publiques, lazy-loadées pour ne pas alourdir le
 *   bundle initial du chat (le user authentifié n'y revient jamais).
 * - / : la chat-page (échiquier + chat) — protégée par authGuard.
 * - ** : redirige tout chemin inconnu vers / (qui re-redirige vers /login si
 *   pas authentifié, via le guard). Évite la 404 nue.
 */
export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./pages/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'signup',
    loadComponent: () =>
      import('./pages/signup/signup.component').then((m) => m.SignupComponent),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/chat-page/chat-page.component').then(
        (m) => m.ChatPageComponent,
      ),
  },
  { path: '**', redirectTo: '' },
];
