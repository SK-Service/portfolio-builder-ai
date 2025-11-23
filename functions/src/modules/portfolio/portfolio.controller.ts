import { Body, Controller, Post } from '@nestjs/common';
import {
  GeneratePortfolioRequestDto,
  PortfolioRecommendationDto,
} from '../../common/dto/portfolio.dto';
import { PortfolioService } from './portfolio.service';

interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

@Controller('portfolio')
export class PortfolioController {
  constructor(private readonly portfolioService: PortfolioService) {}

  @Post('generate')
  async generatePortfolio(
    @Body() request: GeneratePortfolioRequestDto,
  ): Promise<ApiResponse<PortfolioRecommendationDto>> {
    const portfolio = await this.portfolioService.generatePortfolio(request);
    return {
      success: true,
      data: portfolio,
      message: 'Portfolio generated successfully',
    };
  }
}
