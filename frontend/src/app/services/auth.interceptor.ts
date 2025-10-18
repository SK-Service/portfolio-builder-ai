import { HttpInterceptorFn } from '@angular/common/http';
import { environment } from '../../environments/environment';

/**
 * Auth Interceptor - Adds security headers to all outgoing requests
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // Skip interceptor for non-API requests
  if (!req.url.includes(environment.api.baseUrl)) {
    return next(req);
  }

  // Clone request and add security headers
  const authReq = req.clone({
    setHeaders: {
      'X-Portfolio-App-Key': environment.security.appKey,
      'X-Requested-With': 'XMLHttpRequest'
    }
  });

  return next(authReq);
};