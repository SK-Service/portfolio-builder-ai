import { Injectable, Logger } from '@nestjs/common';
import {
  GeneratePortfolioRequestDto,
  PortfolioRecommendationDto,
} from '../../common/dto/portfolio.dto';
import { AgentService } from '../../services/agent/agent.service';
import { MockAgentService } from '../../services/mocks/mock-agent.service';

@Injectable()
export class PortfolioService {
  private readonly logger = new Logger(PortfolioService.name);
  private readonly useMock: boolean;

  constructor(
    private readonly mockAgentService: MockAgentService,
    private readonly agentService: AgentService,
  ) {
    this.useMock = process.env.USE_MOCK_AGENTS === 'true';
    this.logger.log(
      `Portfolio Service initialized. Using ${this.useMock ? 'MOCK' : 'REAL'}agent.`,
    );
  }

  /**
   * Generate portfolio recommendation
   * Uses mock or real agent based on environment.useMockAgents
   */
  async generatePortfolio(
    request: GeneratePortfolioRequestDto,
  ): Promise<PortfolioRecommendationDto> {
    this.logger.log('Generating portfolio...');

    if (this.useMock) {
      this.logger.warn('Using MOCK agent service');
      return this.mockAgentService.generatePortfolioWithDelay(request);
    }

    return this.agentService.generatePortfolio(request);
  }
}
