import {
  HttpException,
  HttpStatus,
  Injectable,
  NestMiddleware,
} from '@nestjs/common';
import { NextFunction, Request, Response } from 'express';
import * as admin from 'firebase-admin';
import { environment } from '../../config/environment';

@Injectable()
export class SecurityMiddleware implements NestMiddleware {
  async use(req: Request, res: Response, next: NextFunction) {
    // Debug logging - remove after fixing
    console.log('Security middleware paths:', {
      path: req.path,
      originalUrl: req.originalUrl,
      baseUrl: req.baseUrl,
      url: req.url,
    });

    // Skip security for health check endpoints
    // Check multiple path variations due to Firebase Functions URL handling
    const isHealthCheck =
      req.path === '/api/health' ||
      req.path === '/health' ||
      req.originalUrl?.endsWith('/health') ||
      req.originalUrl?.endsWith('/api/health');

    if (isHealthCheck) {
      console.log('Security: Skipping health check');
      return next();
    }

    // Skip for OPTIONS (CORS preflight)
    if (req.method === 'OPTIONS') {
      return next();
    }

    // Validate App Check token (primary security)
    const appCheckToken = req.headers['x-firebase-appcheck'] as string;

    if (environment.production) {
      if (!appCheckToken) {
        console.error('Security: Missing App Check token');
        throw new HttpException(
          'Unauthorized: App Check required',
          HttpStatus.UNAUTHORIZED,
        );
      }

      try {
        await admin.appCheck().verifyToken(appCheckToken);
      } catch (error) {
        console.error('Security: Invalid App Check token', error);
        throw new HttpException(
          'Unauthorized: Invalid App Check token',
          HttpStatus.UNAUTHORIZED,
        );
      }
    }

    // Validate app key (secondary check, defense in depth)
    const appKey = req.headers['x-portfolio-app-key'] as string;
    if (!appKey || appKey !== environment.security.requiredAppKey) {
      console.error('Security: Invalid or missing app key');
      throw new HttpException(
        'Unauthorized: Invalid credentials',
        HttpStatus.UNAUTHORIZED,
      );
    }

    next();
  }
}
