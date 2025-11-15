import { HttpModule } from '@nestjs/axios';
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { AgentService } from '../../services/agent/agent.service';
import { MockAgentService } from '../../services/mocks/mock-agent.service';
import { PortfolioController } from './portfolio.controller';
import { PortfolioService } from './portfolio.service';

@Module({
  imports: [HttpModule, ConfigModule],
  controllers: [PortfolioController],
  providers: [PortfolioService, AgentService, MockAgentService],
})
export class PortfolioModule {}
