import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { ExpressAdapter } from '@nestjs/platform-express';
import dotenv from 'dotenv';
import express from 'express';
import * as admin from 'firebase-admin';
import { onRequest } from 'firebase-functions/v2/https';

// Load env in non-production
if (process.env.NODE_ENV !== 'production') {
  dotenv.config();
}

import { AppModule } from './app.module';
import { environment } from './config/environment';

// Initialize Firebase Admin (required for App Check verification)
if (!admin.apps.length) {
  admin.initializeApp();
}

const expressApp = express();

const createNestServer = async (
  expressInstance: express.Express,
): Promise<void> => {
  const app = await NestFactory.create(
    AppModule,
    new ExpressAdapter(expressInstance),
  );

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
      'X-Firebase-AppCheck',
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

  await app.init();
  console.log('NestJS BFF initialized for Firebase Functions');
};

// Initialize NestJS on cold start
let isInitialized = false;
const ensureInitialized = async (): Promise<void> => {
  if (!isInitialized) {
    await createNestServer(expressApp);
    isInitialized = true;
  }
};

// Initialize immediately for Firebase Functions
void ensureInitialized();

// Export the Firebase Function (v2)
export const api = onRequest(
  {
    region: 'us-central1',
    timeoutSeconds: 60,
    memory: '512MiB',
  },
  expressApp,
);

// Local development server (only runs when not in Firebase Functions environment)
if (process.env.FUNCTIONS_EMULATOR !== 'true' && !process.env.FUNCTION_TARGET) {
  const bootstrap = async (): Promise<void> => {
    await createNestServer(expressApp);
    const port = process.env.PORT ?? 5001;
    expressApp.listen(port, () => {
      console.log(`BFF Server running on http://localhost:${String(port)}/api`);
      console.log(
        `Environment: ${environment.production ? 'production' : 'development'}`,
      );
      console.log(`Using mock agents: ${String(environment.useMockAgents)}`);
    });
  };
  bootstrap().catch((err: unknown) => {
    console.error('Failed to start BFF server:', err);
    process.exit(1);
  });
}
