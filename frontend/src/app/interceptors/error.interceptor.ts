import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { catchError, throwError } from 'rxjs';
import { LoggerService } from '../services/logger.service';

/**
 * Error Interceptor - Global error handling for HTTP requests
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const snackBar = inject(MatSnackBar);
  const logger = inject(LoggerService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let errorMessage = 'An error occurred';

      if (error.error instanceof ErrorEvent) {
        // Client-side error
        errorMessage = `Error: ${error.error.message}`;
      } else {
        // Server-side error
        errorMessage = error.error?.message || `Error Code: ${error.status}\nMessage: ${error.message}`;
      }

      // Log error
      logger.error('HTTP Error:', {
        url: req.url,
        status: error.status,
        message: errorMessage,
        error: error
      });

      // Show user-friendly error message
      snackBar.open(errorMessage, 'Close', {
        duration: 5000,
        panelClass: ['error-snackbar'],
        horizontalPosition: 'center',
        verticalPosition: 'top'
      });

      return throwError(() => error);
    })
  );
};