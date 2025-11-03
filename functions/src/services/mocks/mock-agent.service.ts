import { Injectable } from '@nestjs/common';
import {
  GeneratePortfolioRequestDto,
  PortfolioRecommendationDto,
  ProjectedGrowthDto,
  RiskTolerance,
} from '../../common/dto/portfolio.dto';
import {
  adjustReturnForRisk,
  generateAllocations,
  mockStocksByCountry,
} from './mock-data';

@Injectable()
export class MockAgentService {
  /**
   * Generate mock portfolio based on user input
   */
  generatePortfolio(
    request: GeneratePortfolioRequestDto,
  ): PortfolioRecommendationDto {
    const { riskTolerance, investmentHorizonYears, country, investmentAmount } =
      request;

    const availableStocks =
      mockStocksByCountry[country] || mockStocksByCountry['USA'];

    // Select number of stocks based on risk
    const numberOfStocks =
      riskTolerance === RiskTolerance.Low
        ? 6
        : riskTolerance === RiskTolerance.High
          ? 4
          : 5;
    // Filter stocks based on risk tolerance
    let filteredStocks = [...availableStocks];
    if (riskTolerance === RiskTolerance.Low) {
      filteredStocks = filteredStocks.filter(
        (s) =>
          ['Healthcare', 'Consumer Goods', 'Financial Services'].includes(
            s.sector,
          ) || s.baseReturn < 12,
      );
    } else if (riskTolerance === RiskTolerance.High) {
      filteredStocks = filteredStocks.filter(
        (s) =>
          ['Technology', 'Consumer Discretionary', 'Automotive'].includes(
            s.sector,
          ) || s.baseReturn > 10,
      );
    }

    if (filteredStocks.length < numberOfStocks) {
      filteredStocks = availableStocks;
    }

    // Shuffle and select
    const shuffled = filteredStocks.sort(() => 0.5 - Math.random());
    const selectedStocks = shuffled.slice(0, numberOfStocks);

    // Generate allocations
    const allocations = generateAllocations(numberOfStocks, riskTolerance);

    // Generate recommendations
    const recommendations = selectedStocks.map((stock, index) => ({
      symbol: stock.symbol,
      companyName: stock.companyName,
      allocation: allocations[index],
      expectedReturn: adjustReturnForRisk(stock.baseReturn, riskTolerance),
      sector: stock.sector,
      country: country,
    }));

    // Calculate total return
    const totalExpectedReturn = recommendations.reduce(
      (total, stock) => total + (stock.expectedReturn * stock.allocation) / 100,
      0,
    );

    // Generate projected growth
    const projectedGrowth: ProjectedGrowthDto[] = [];
    for (let year = 0; year <= investmentHorizonYears; year++) {
      const projectedValue =
        investmentAmount * Math.pow(1 + totalExpectedReturn / 100, year);
      projectedGrowth.push({
        year,
        projectedValue: Math.round(projectedValue),
      });
    }

    const riskScore =
      riskTolerance === RiskTolerance.Low
        ? 3.2
        : riskTolerance === RiskTolerance.High
          ? 8.1
          : 5.8;

    return {
      recommendations,
      totalExpectedReturn: Math.round(totalExpectedReturn * 10) / 10,
      riskScore,
      projectedGrowth,
      generatedAt: new Date().toISOString(),
    };
  }

  /**
   * Simulate network delay (realistic mock behavior)
   */
  async generatePortfolioWithDelay(
    request: GeneratePortfolioRequestDto,
  ): Promise<PortfolioRecommendationDto> {
    // Simulate 2-second processing time
    await new Promise((resolve) => setTimeout(resolve, 2000));
    return this.generatePortfolio(request);
  }
}
