import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap } from 'rxjs';

import { AuthService } from '../services/auth.service';

/**
 * Intercepteur HTTP : injecte le Bearer token et gère l'expiration.
 *
 * 401 → on logout (clear token + redirect /login). L'utilisateur retape son
 *       mdp, c'est la voie de moindre surprise pour un POC sans refresh tokens.
 * 429 → on laisse l'appelant gérer (ChatService affiche un message dédié pour
 *       le quota épuisé sur /chat ; les pages signup pour leur propre 429).
 *
 * IMPORTANT : on injecte le header sur TOUTES les requêtes /api/v1/*, y compris
 * /auth/signup et /auth/login (le backend ignore le Bearer sur ces routes
 * publiques). Filtrer par URL serait fragile, le backend tranche.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  const token = auth.token();
  const authed = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authed).pipe(
    tap({
      error: (err: HttpErrorResponse) => {
        // Le 401 sur /auth/login lui-même = mauvais mdp, pas un token expiré.
        // On évite alors de logout (sinon ça déclenche un redirect intempestif
        // pendant que la page Login est en train d'afficher l'erreur).
        if (err.status === 401 && !req.url.endsWith('/auth/login')) {
          auth.logout();
        }
      },
    }),
  );
};
