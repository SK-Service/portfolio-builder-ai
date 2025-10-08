// portfolio-builder-ai/frontend/src/app/guards/rate-limit.guard.ts

import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { CanActivate, Router } from '@angular/router';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { RateLimitService } from '../services/rate-limit.service';

@Injectable({
  providedIn: 'root'
})
export class RateLimitGuard implements CanActivate {

  constructor(
    private rateLimitService: RateLimitService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {}

  canActivate(): Observable<boolean> {
    return this.rateLimitService.checkRateLimit().pipe(
      map(({ allowed, attemptsRemaining }) => {
        if (allowed) {
          return true;
        } else {
          this.showRateLimitMessage(attemptsRemaining);
          this.router.navigate(['/']);
          return false;
        }
      }),
      catchError(error => {
        console.warn('Rate limit check failed, allowing access:', error);
        return of(true); // Allow access if rate limit check fails
      })
    );
  }

  private showRateLimitMessage(attemptsRemaining: number): void {
    const message = attemptsRemaining === 0 
      ? 'You have reached your free usage limit. Please try again later or contact support.'
      : `You have ${attemptsRemaining} attempt${attemptsRemaining !== 1 ? 's' : ''} remaining.`;
    
    this.snackBar.open(message, 'OK', {
      duration: 8000,
      panelClass: ['rate-limit-snackbar']
    });
  }
}