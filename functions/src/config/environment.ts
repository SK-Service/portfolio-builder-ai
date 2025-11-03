export const environment = {
  production: false,

  // Mock toggle - CRITICAL for development
  useMockAgents: true, // Set to false when agents ready

  // Firebase configuration
  firebase: {
    projectId: process.env.FIREBASE_PROJECT_ID || 'portfolio-builder-ai',
    databaseURL: 'https://portfolio-builder-ai.firebaseio.com',
  },

  // Security
  security: {
    allowedOrigins: [
      'https://portfolio-builder-ai.web.app',
      'https://portfolio-builder-ai.firebaseapp.com',
      'http://localhost:4200', // Local Angular development
    ],
    requiredAppKey:
      process.env.PORTFOLIO_APP_KEY || 'dev-portfolio-app-key-12345',
  },

  // Rate limiting
  rateLimit: {
    maxAttemptsPerFingerprint: 2,
    windowHours: 24,
  },

  // Agent configuration (for future)
  agents: {
    orchestratorUrl:
      process.env.AGENT_ORCHESTRATOR_URL || 'http://localhost:8080',
    timeout: 30000, // 30 seconds
  },

  // Firestore collections
  collections: {
    appConfig: 'app_config',
    rateLimits: 'rate_limits',
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'debug',
    enableRequestLogging: true,
  },
};
