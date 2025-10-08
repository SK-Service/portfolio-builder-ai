// portfolio-builder-ai/frontend/src/environments/environment.ts

export const environment = {
  production: false,
  firebase: {
    apiKey: "your-dev-api-key",
    authDomain: "portfolio-builder-staging.firebaseapp.com",
    projectId: "portfolio-builder-staging",
    storageBucket: "portfolio-builder-staging.appspot.com",
    messagingSenderId: "123456789",
    appId: "your-dev-app-id"
  },
  api: {
    baseUrl: 'http://localhost:5001/portfolio-builder-staging/us-central1',
    timeout: 30000
  },
  rateLimit: {
    defaultMaxAttempts: 2,
    windowHours: 24
  },
  features: {
    enableAnalytics: false,
    enableLogging: true,
    mockData: true // Use mock data in development
  }
};