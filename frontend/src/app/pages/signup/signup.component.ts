import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../services/auth.service';

/**
 * Page /signup — création de compte.
 *
 * Validators reflètent les contraintes Pydantic backend (`UserCreate`) :
 * - email valide,
 * - password >= 8 caractères.
 *
 * Cas d'erreur explicites :
 * - 409 : email déjà pris,
 * - 429 : rate-limit IP (5/heure), demander de revenir plus tard,
 * - 0 / 5xx : backend indispo.
 */
@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="min-h-dvh flex items-center justify-center bg-slate-50 px-4">
      <div class="w-full max-w-sm bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <div class="flex items-center gap-3 mb-6">
          <img src="logo.png" alt="Chess Agent" class="w-12 h-12 object-contain" />
          <div>
            <h1 class="text-xl font-bold text-slate-900">Créer un compte</h1>
            <p class="text-xs text-slate-500">Chess Agent · FFE</p>
          </div>
        </div>

        <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-4">
          <label class="block">
            <span class="block text-sm font-medium text-slate-700 mb-1">Email</span>
            <input
              type="email"
              autocomplete="email"
              formControlName="email"
              class="w-full px-3 py-2 rounded-lg border border-slate-300
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </label>
          <label class="block">
            <span class="block text-sm font-medium text-slate-700 mb-1">
              Mot de passe
              <span class="text-xs text-slate-500 font-normal">(8 caractères minimum)</span>
            </span>
            <input
              type="password"
              autocomplete="new-password"
              formControlName="password"
              class="w-full px-3 py-2 rounded-lg border border-slate-300
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </label>

          @if (error()) {
            <div class="px-3 py-2 rounded-lg bg-rose-50 border border-rose-200 text-sm text-rose-800">
              {{ error() }}
            </div>
          }

          <button
            type="submit"
            class="w-full px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white
                   disabled:bg-slate-300 disabled:cursor-not-allowed transition
                   text-sm font-medium
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            [disabled]="form.invalid || loading()"
          >
            {{ loading() ? 'Création…' : 'Créer mon compte' }}
          </button>
        </form>

        <p class="mt-6 text-sm text-center text-slate-600">
          Déjà inscrit ?
          <a routerLink="/login" class="font-medium text-blue-600 hover:text-blue-700">
            Connecte-toi
          </a>
        </p>
      </div>
    </div>
  `,
})
export class SignupComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  submit(): void {
    if (this.form.invalid || this.loading()) return;
    this.loading.set(true);
    this.error.set(null);

    this.auth.signup(this.form.getRawValue()).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/']);
      },
      error: (err: HttpErrorResponse) => {
        this.loading.set(false);
        if (err.status === 409) {
          this.error.set('Cet email est déjà utilisé. Connecte-toi ou choisis-en un autre.');
        } else if (err.status === 429) {
          this.error.set(
            'Trop de tentatives depuis ton réseau. Réessaie dans une heure.',
          );
        } else if (err.status === 0) {
          this.error.set('Backend injoignable. Réessaie dans un instant.');
        } else if (err.status === 422) {
          this.error.set('Email invalide ou mot de passe trop court (8 caractères min).');
        } else {
          this.error.set(`Erreur ${err.status}. Réessaie plus tard.`);
        }
      },
    });
  }
}
