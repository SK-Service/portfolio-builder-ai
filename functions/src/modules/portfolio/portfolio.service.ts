import { Injectable } from '@nestjs/common';
import {
  GeneratePortfolioRequestDto,
  PortfolioRecommendationDto,
} from '../../common/dto/portfolio.dto';
import { environment } from '../../config/environment';
import { MockAgentService } from '../../services/mocks/mock-agent.service';

@Injectable()
export class PortfolioService {
  constructor(private readonly mockAgentService: MockAgentService) {}

  /**
   * Generate portfolio recommendation
   * Uses mock or real agent based on environment.useMockAgents
   */
  async generatePortfolio(
    request: GeneratePortfolioRequestDto,
  ): Promise<PortfolioRecommendationDto> {
    if (environment.useMockAgents) {
      console.log('Using mock agent for portfolio generation');
      return this.mockAgentService.generatePortfolioWithDelay(request);
    } else {
      console.log('Using real agent orchestrator (not implemented yet)');
      // TODO: Call agent orchestrator in Step 10
      throw new Error('Real agent integration not yet implemented');
    }
  }
}
