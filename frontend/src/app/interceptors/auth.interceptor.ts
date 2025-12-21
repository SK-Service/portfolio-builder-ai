import { HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { from, switchMap } from "rxjs";
import { environment } from "../../environments/environment";
import { AppCheckService } from "../services/app-check.service";

/**
 * Auth Interceptor - Adds security headers to all outgoing requests
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // Skip interceptor for non-API requests
  if (!req.url.includes(environment.api.baseUrl)) {
    return next(req);
  }

  const appCheckService = inject(AppCheckService);

  return from(appCheckService.getAppCheckToken()).pipe(
    switchMap((appCheckToken) => {
      const headers: Record<string, string> = {
        "X-Portfolio-App-Key": environment.security.appKey,
        "X-Requested-With": "XMLHttpRequest",
      };

      if (appCheckToken) {
        headers["X-Firebase-AppCheck"] = appCheckToken;
      }

      const authReq = req.clone({ setHeaders: headers });
      return next(authReq);
    })
  );
};
