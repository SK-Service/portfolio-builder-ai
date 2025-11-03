import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import * as dotenv from 'dotenv';

if (process.env.NODE_ENV !== 'production') {
  dotenv.config();
}

import { AppModule } from './app.module';
import { environment } from './config/environment';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Global prefix for all routes
  app.setGlobalPrefix('api');

  // CORS configuration
  app.enableCors({
    origin: (
      origin: string | undefined,
      callback: (err: Error | null, allow?: boolean) => void,
    ) => {
      // Allow requests with no origin in development only (Postman, curl)
      if (!origin && !environment.production) {
        return callback(null, true);
      }

      // Production: Require origin header
      if (!origin) {
        console.error('CORS: Origin header required in production');
        return callback(new Error('Origin header required'));
      }
      // Check if origin is in allowed list
      if (environment.security.allowedOrigins.includes(origin)) {
        callback(null, true);
      } else {
        console.error(`CORS: Blocked request from origin: ${origin}`);
        callback(new Error('Not allowed by CORS'));
      }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: [
      'Content-Type',
      'Authorization',
      'X-Portfolio-App-Key',
      'X-Requested-With',
    ],
  });

  // Global validation pipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );

  const port = process.env.PORT || 5001;
  await app.listen(port);

  console.log(`BFF Server running on http://localhost:${port}/api`);
  console.log(
    `Environment: ${environment.production ? 'production' : 'development'}`,
  );
  console.log(`Using mock agents: ${environment.useMockAgents}`);
  console.log(`CORS: No-origin allowed: ${!environment.production}`);
}

bootstrap().catch((err) => {
  console.error('Failed to start BFF server:', err);
  process.exit(1);
});
