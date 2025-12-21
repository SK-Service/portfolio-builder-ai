export const environment = {
  production: process.env.NODE_ENV === 'production',

  // Mock toggle - set to false for production
  useMockAgents: process.env.USE_MOCK_AGENTS === 'true',

  // Firebase configuration
  firebase: {
    projectId: process.env.FIREBASE_PROJECT_ID || 'portfolio-builder-ai-1da81',
  },

  // Security
  security: {
    allowedOrigins: [
      'https://portfolio-builder-ai-1da81.web.app',
      'https://portfolio-builder-ai-1da81.firebaseapp.com',
      'http://localhost:4200',
      'http://localhost:5000',
    ],
    requiredAppKey:
      process.env.PORTFOLIO_APP_KEY || 'dev-key-change-in-production',
  },

  // Rate limiting
  rateLimit: {
    maxAttemptsPerFingerprint: 2,
    windowHours: 24,
  },

  // Agent configuration
  agents: {
    apiKey: process.env.AGENT_API_KEY || '',
    generatePortfolioUrl:
      process.env.AGENT_FUNCTION_URL ||
      `https://us-central1-${process.env.FIREBASE_PROJECT_ID || 'portfolio-builder-ai-1da81'}.cloudfunctions.net/generatePortfolio`,
    timeout: 60000,
  },

  // Firestore collections
  collections: {
    appConfig: 'app_config',
    rateLimits: 'rate_limits',
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    enableRequestLogging: process.env.NODE_ENV !== 'production',
  },
};
