import {
  Injectable,
  NestMiddleware,
  UnauthorizedException,
} from '@nestjs/common';
import { NextFunction, Request, Response } from 'express';
import { environment } from '../../config/environment';

@Injectable()
export class SecurityMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    // Skip security check for health endpoint
    if (req.path === '/health' || req.path === '/') {
      return next();
    }

    // Check for required app key header
    const appKey = req.headers['x-portfolio-app-key'] as string;

    const expectedKey = environment.security.requiredAppKey;

    console.log('DEBUG - Received key:', appKey?.substring(0, 20) + '...');
    console.log('DEBUG - Expected key:', expectedKey?.substring(0, 20) + '...');
    console.log('DEBUG - Keys match:', appKey === expectedKey);

    const requestedWith = req.headers['x-requested-with'] as string;

    // Validate app key
    if (!appKey || appKey !== environment.security.requiredAppKey) {
      console.error('Security: Invalid or missing X-Portfolio-App-Key header');
      throw new UnauthorizedException({
        statusCode: 401,
        message: 'Invalid or missing authentication credentials',
        error: 'Unauthorized',
      });
    }

    // Validate X-Requested-With header (CSRF protection)
    if (!requestedWith || requestedWith !== 'XMLHttpRequest') {
      console.error('Security: Invalid or missing X-Requested-With header');
      throw new UnauthorizedException({
        statusCode: 401,
        message: 'Invalid request headers',
        error: 'Unauthorized',
      });
    }

    console.log(`Security: Request authorized for ${req.method} ${req.path}`);
    next();
  }
}
