export interface HealthResponse {
  status: string;
  service: string;
  timestamp: string;
  environment: {
    production: boolean;
    useMockAgents: boolean;
    firebaseProject: string;
  };
}

export interface RootResponse {
  service: string;
  version: string;
  status: string;
  endpoints: {
    health: string;
    config: string;
    portfolio: string;
    rateLimit: string;
  };
}
