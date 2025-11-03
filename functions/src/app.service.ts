import { Injectable } from '@nestjs/common';
import { HealthResponse } from './common/types/response.types';
import { environment } from './config/environment';

@Injectable()
export class AppService {
  getHealth(): HealthResponse {
    return {
      status: 'ok',
      service: 'portfolio-bff',
      timestamp: new Date().toISOString(),
      environment: {
        production: environment.production,
        useMockAgents: environment.useMockAgents,
        firebaseProject: environment.firebase.projectId,
      },
    };
  }
}
