import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import {
  PortfolioRecommendation,
  RiskAssessment
} from '../shared/models';
import {
  GeneratePortfolioRequest
} from '../shared/models/api-contracts';
import { PortfolioApiService } from './api/portfolio-api.service';
import { LoggerService } from './logger.service';

@Injectable({
  providedIn: 'root'
})
export class PortfolioService {

  constructor(
    private portfolioApiService: PortfolioApiService,
    private logger: LoggerService
  ) {}

  /**
   * Generate portfolio recommendation
   * This calls the BFF which orchestrates the AI agents
   */
  generatePortfolioRecommendation(riskAssessment: RiskAssessment): Observable<PortfolioRecommendation> {
    this.logger.debug('PortfolioService: Generating portfolio for', riskAssessment);

    // Build API request
    const request: GeneratePortfolioRequest = {
      riskTolerance: riskAssessment.riskTolerance,
      investmentHorizonYears: riskAssessment.investmentHorizonYears,
      country: riskAssessment.country,
      investmentAmount: riskAssessment.investmentAmount,
      currency: riskAssessment.currency
    };

    // Call BFF API
    return this.portfolioApiService.generatePortfolio(request).pipe(
      map(response => {
        if (response.success && response.data) {
          this.logger.info('PortfolioService: Portfolio generated successfully', response.data);
          
          // Transform DTO to domain model
          const portfolio: PortfolioRecommendation = {
            recommendations: response.data.recommendations.map(dto => ({
              symbol: dto.symbol,
              companyName: dto.companyName,
              allocation: dto.allocation,
              expectedReturn: dto.expectedReturn,
              sector: dto.sector,
              country: dto.country
            })),
            totalExpectedReturn: response.data.totalExpectedReturn,
            riskScore: response.data.riskScore,
            projectedGrowth: response.data.projectedGrowth.map(dto => ({
              year: dto.year,
              projectedValue: dto.projectedValue
            }))
          };

          return portfolio;
        } else {
          this.logger.error('PortfolioService: BFF returned unsuccessful response');
          throw new Error('Failed to generate portfolio');
        }
      }),
      catchError(error => {
        this.logger.error('PortfolioService: Error generating portfolio', error);
        throw error;
      })
    );
  }
}