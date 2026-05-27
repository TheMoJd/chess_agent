import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

import { environment } from '../../environments/environment';
import { AuthCredentials, Token, UserPublic } from '../models/user.model';

/**
 * Gère l'identité utilisateur côté front : signup, login, logout, profil.
 *
 * Persistance : le token JWT + le user public sont stockés en localStorage
 * (mêmes clés réutilisables après refresh). Pattern symétrique à
 * SessionService pour l'identifiant de thread LangGraph.
 *
 * Le `currentUser` (et notamment son compteur `messages_used`) est rafraîchi
 * par ChatService après chaque /chat OK, pour que le header reflète le quota
 * live sans qu'on ait à le calculer côté front.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly base = `${environment.apiBaseUrl}/auth`;

  private readonly TOKEN_KEY = 'chess_agent_jwt';
  private readonly USER_KEY = 'chess_agent_user';

  readonly token = signal<string | null>(this.loadToken());
  readonly currentUser = signal<UserPublic | null>(this.loadUser());

  /** True si un token est présent. NE garantit PAS sa validité (peut être expiré
   * côté serveur) — l'interceptor relègue alors via /login sur 401. */
  readonly isAuthenticated = computed(() => !!this.token());

  signup(creds: AuthCredentials): Observable<Token> {
    return this.http
      .post<Token>(`${this.base}/signup`, creds)
      .pipe(tap((res) => this.persistSession(res)));
  }

  login(creds: AuthCredentials): Observable<Token> {
    return this.http
      .post<Token>(`${this.base}/login`, creds)
      .pipe(tap((res) => this.persistSession(res)));
  }

  /**
   * Rafraîchit le profil utilisateur depuis le backend.
   *
   * À appeler après chaque /chat OK pour mettre à jour le badge quota du
   * header (le backend retourne le décompte canonique, on ne le recalcule
   * pas localement pour éviter toute désync).
   */
  refreshMe(): Observable<UserPublic> {
    return this.http
      .get<UserPublic>(`${this.base}/me`)
      .pipe(tap((user) => this.persistUser(user)));
  }

  /** Clear tout : token, user, localStorage. Redirige vers /login. */
  logout(): void {
    this.token.set(null);
    this.currentUser.set(null);
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(this.TOKEN_KEY);
      localStorage.removeItem(this.USER_KEY);
    }
    this.router.navigate(['/login']);
  }

  private persistSession(res: Token): void {
    this.token.set(res.access_token);
    this.persistUser(res.user);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(this.TOKEN_KEY, res.access_token);
    }
  }

  private persistUser(user: UserPublic): void {
    this.currentUser.set(user);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    }
  }

  private loadToken(): string | null {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private loadUser(): UserPublic | null {
    if (typeof localStorage === 'undefined') return null;
    const raw = localStorage.getItem(this.USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as UserPublic;
    } catch {
      return null;
    }
  }
}
