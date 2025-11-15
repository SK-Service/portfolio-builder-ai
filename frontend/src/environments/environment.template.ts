// TEMPLATE - Copy to environment.ts and fill in your values
// DO NOT commit environment.ts to Git!

export const environment = {
  production: false,
  firebase: {
    apiKey: "YOUR_FIREBASE_API_KEY",
    authDomain: "projectID.firebaseapp.com",
    projectId: "ProjectID",
    storageBucket: "projectID.firebasestorage.app",
    messagingSenderId: "1234513413241234",
    appId: "2:asdfasdfsadf123441234123412414141241",
    measurementId: "G-0RHSN27PTC",
  },

  api: {
    baseUrl: "http://localhost:5001/api",
    endpoints: {
      portfolio: "/portfolio",
      config: "/config",
      rateLimit: "/rate-limit",
    },
    timeout: 30000,
    retryAttempts: 2,
  },

  features: {
    useMockData: false,
    enableAnalytics: false,
    enableLogging: true,
  },

  security: {
    appKey: "YOUR_BFF_APP_KEY",
  },
};
