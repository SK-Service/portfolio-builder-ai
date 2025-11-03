import { Controller, Get } from '@nestjs/common';
import { AppService } from './app.service';
import type {
  HealthResponse,
  RootResponse,
} from './common/types/response.types';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get('health')
  getHealth(): HealthResponse {
    return this.appService.getHealth();
  }

  @Get()
  getRoot(): RootResponse {
    return {
      service: 'Portfolio Builder BFF',
      version: '1.0.0',
      status: 'running',
      endpoints: {
        health: '/api/health',
        config: '/api/config',
        portfolio: '/api/portfolio/generate',
        rateLimit: '/api/rate-limit/*',
      },
    };
  }
}
