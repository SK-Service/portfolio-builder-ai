import { Body, Controller, Post } from '@nestjs/common';
import {
  GeneratePortfolioRequestDto,
  PortfolioRecommendationDto,
} from '../../common/dto/portfolio.dto';
import { PortfolioService } from './portfolio.service';

@Controller('portfolio')
export class PortfolioController {
  constructor(private readonly portfolioService: PortfolioService) {}

  @Post('generate')
  async generatePortfolio(
    @Body() request: GeneratePortfolioRequestDto,
  ): Promise<PortfolioRecommendationDto> {
    return this.portfolioService.generatePortfolio(request);
  }
}
