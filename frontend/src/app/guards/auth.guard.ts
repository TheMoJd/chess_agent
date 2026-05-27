import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../services/auth.service';

/**
 * Guard fonctionnel : bloque l'accès à /  si pas authentifié.
 *
 * On vérifie uniquement la présence d'un token côté client. Si le token est
 * expiré côté serveur, c'est l'intercepteur qui logout au premier 401 reçu —
 * pas la peine de duplicater la logique de validité ici.
 */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) return true;
  router.navigate(['/login']);
  return false;
};
