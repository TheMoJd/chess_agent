import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  importProvidersFrom,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { NgxChessBoardModule } from 'ngx-chess-board';

import { routes } from './app.routes';
import { authInterceptor } from './interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    // L'intercepteur authInterceptor injecte le Bearer token sur toutes les
    // requêtes HTTP — c'est pour ça qu'on n'a plus à toucher chat.service.ts.
    provideHttpClient(withInterceptors([authInterceptor])),
    importProvidersFrom(NgxChessBoardModule.forRoot()),
  ],
};
