import { Module } from '@nestjs/common';
import { MockAgentService } from '../../services/mocks/mock-agent.service';
import { PortfolioController } from './portfolio.controller';
import { PortfolioService } from './portfolio.service';

@Module({
  controllers: [PortfolioController],
  providers: [PortfolioService, MockAgentService],
})
export class PortfolioModule {}
