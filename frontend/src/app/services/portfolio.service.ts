// portfolio-builder-ai/frontend/src/app/services/portfolio.service.ts

import { Injectable } from '@angular/core';
import { delay, Observable, of } from 'rxjs';
import { environment } from '../../environments/environment';
import { PortfolioRecommendation, ProjectedGrowth, RiskAssessment, StockRecommendation } from '../shared/models';

@Injectable({
  providedIn: 'root'
})
export class PortfolioService {

  private readonly mockStocks = {
    'USA': [
      { symbol: 'AAPL', companyName: 'Apple Inc.', sector: 'Technology', baseReturn: 12.5 },
      { symbol: 'MSFT', companyName: 'Microsoft Corporation', sector: 'Technology', baseReturn: 11.8 },
      { symbol: 'GOOGL', companyName: 'Alphabet Inc.', sector: 'Technology', baseReturn: 13.2 },
      { symbol: 'AMZN', companyName: 'Amazon.com Inc.', sector: 'Consumer Discretionary', baseReturn: 14.1 },
      { symbol: 'TSLA', companyName: 'Tesla Inc.', sector: 'Automotive', baseReturn: 18.5 },
      { symbol: 'JPM', companyName: 'JPMorgan Chase & Co.', sector: 'Financial Services', baseReturn: 9.2 },
      { symbol: 'JNJ', companyName: 'Johnson & Johnson', sector: 'Healthcare', baseReturn: 7.8 },
      { symbol: 'V', companyName: 'Visa Inc.', sector: 'Financial Services', baseReturn: 10.4 }
    ],
    'EU': [
      { symbol: 'ASML', companyName: 'ASML Holding N.V.', sector: 'Technology', baseReturn: 15.2 },
      { symbol: 'SAP', companyName: 'SAP SE', sector: 'Technology', baseReturn: 9.8 },
      { symbol: 'NESN', companyName: 'Nestlé S.A.', sector: 'Consumer Goods', baseReturn: 6.5 },
      { symbol: 'RYDAF', companyName: 'Royal Dutch Shell', sector: 'Energy', baseReturn: 8.2 },
      { symbol: 'NOVN', companyName: 'Novartis AG', sector: 'Healthcare', baseReturn: 7.1 },
      { symbol: 'LVMUY', companyName: 'LVMH', sector: 'Consumer Discretionary', baseReturn: 12.8 }
    ],
    'Canada': [
      { symbol: 'SHOP', companyName: 'Shopify Inc.', sector: 'Technology', baseReturn: 16.3 },
      { symbol: 'RY', companyName: 'Royal Bank of Canada', sector: 'Financial Services', baseReturn: 8.7 },
      { symbol: 'CNR', companyName: 'Canadian National Railway', sector: 'Transportation', baseReturn: 9.5 },
      { symbol: 'BNS', companyName: 'Bank of Nova Scotia', sector: 'Financial Services', baseReturn: 8.2 },
      { symbol: 'TRI', companyName: 'Thomson Reuters Corp.', sector: 'Information Services', baseReturn: 10.1 }
    ],
    'India': [
      { symbol: 'TCS', companyName: 'Tata Consultancy Services', sector: 'Technology', baseReturn: 14.8 },
      { symbol: 'RELIANCE', companyName: 'Reliance Industries Ltd.', sector: 'Energy', baseReturn: 13.2 },
      { symbol: 'INFY', companyName: 'Infosys Limited', sector: 'Technology', baseReturn: 13.9 },
      { symbol: 'HDFC', companyName: 'HDFC Bank Limited', sector: 'Financial Services', baseReturn: 11.5 },
      { symbol: 'BHARTIARTL', companyName: 'Bharti Airtel Limited', sector: 'Telecommunications', baseReturn: 10.8 },
      { symbol: 'ITC', companyName: 'ITC Limited', sector: 'Consumer Goods', baseReturn: 8.9 }
    ]
  };

  constructor() {}

  /**
   * Generates portfolio recommendation based on risk assessment
   */
  generatePortfolioRecommendation(riskAssessment: RiskAssessment): Observable<PortfolioRecommendation> {
    // Simulate API call delay
    const simulationDelay = environment.features.mockData ? 2000 : 100;
    
    return of(this.createMockPortfolio(riskAssessment)).pipe(
      delay(simulationDelay)
    );
  }

  private createMockPortfolio(riskAssessment: RiskAssessment): PortfolioRecommendation {
    const availableStocks = this.mockStocks[riskAssessment.country] || this.mockStocks['USA'];
    const numberOfStocks = this.getNumberOfStocks(riskAssessment.riskTolerance);
    const selectedStocks = this.selectStocks(availableStocks, numberOfStocks, riskAssessment.riskTolerance);
    
    const recommendations = this.generateStockRecommendations(selectedStocks, riskAssessment);
    const totalExpectedReturn = this.calculatePortfolioReturn(recommendations);
    const projectedGrowth = this.generateProjectedGrowth(
      riskAssessment.investmentAmount,
      totalExpectedReturn,
      riskAssessment.investmentHorizonYears
    );

    return {
      recommendations,
      totalExpectedReturn,
      riskScore: this.calculateRiskScore(riskAssessment.riskTolerance),
      projectedGrowth
    };
  }

  private getNumberOfStocks(riskTolerance: string): number {
    switch (riskTolerance) {
      case 'Low': return 6; // More diversification
      case 'Medium': return 5;
      case 'High': return 4; // More concentrated
      default: return 5;
    }
  }

  private selectStocks(availableStocks: any[], count: number, riskTolerance: string): any[] {
    let filteredStocks = [...availableStocks];
    
    // Filter based on risk tolerance
    if (riskTolerance === 'Low') {
      // Prefer stable sectors
      filteredStocks = filteredStocks.filter(stock => 
        ['Healthcare', 'Consumer Goods', 'Financial Services'].includes(stock.sector) ||
        stock.baseReturn < 12
      );
    } else if (riskTolerance === 'High') {
      // Prefer growth sectors
      filteredStocks = filteredStocks.filter(stock => 
        ['Technology', 'Consumer Discretionary', 'Automotive'].includes(stock.sector) ||
        stock.baseReturn > 10
      );
    }
    
    // If filtering resulted in too few stocks, add some back
    if (filteredStocks.length < count) {
      filteredStocks = availableStocks;
    }
    
    // Shuffle and select
    const shuffled = filteredStocks.sort(() => 0.5 - Math.random());
    return shuffled.slice(0, count);
  }

  private generateStockRecommendations(selectedStocks: any[], riskAssessment: RiskAssessment): StockRecommendation[] {
    const allocations = this.generateAllocations(selectedStocks.length, riskAssessment.riskTolerance);
    
    return selectedStocks.map((stock, index) => ({
      symbol: stock.symbol,
      companyName: stock.companyName,
      allocation: allocations[index],
      expectedReturn: this.adjustReturnForRisk(stock.baseReturn, riskAssessment.riskTolerance),
      sector: stock.sector,
      country: riskAssessment.country
    }));
  }

  private generateAllocations(numberOfStocks: number, riskTolerance: string): number[] {
    let allocations: number[] = [];
    
    if (riskTolerance === 'Low') {
      // More even distribution
      const baseAllocation = 100 / numberOfStocks;
      allocations = Array(numberOfStocks).fill(baseAllocation);
      
      // Add small random variation
      allocations = allocations.map(allocation => 
        allocation + (Math.random() - 0.5) * 4
      );
    } else if (riskTolerance === 'High') {
      // More concentrated positions
      allocations.push(35 + Math.random() * 10); // Largest position
      allocations.push(25 + Math.random() * 8);  // Second largest
      
      const remaining = 100 - allocations.reduce((sum, curr) => sum + curr, 0);
      const remainingStocks = numberOfStocks - allocations.length;
      
      for (let i = 0; i < remainingStocks; i++) {
        allocations.push((remaining / remainingStocks) + (Math.random() - 0.5) * 3);
      }
    } else {
      // Medium risk - balanced approach
      const baseAllocation = 100 / numberOfStocks;
      allocations = Array(numberOfStocks).fill(baseAllocation);
      
      // Moderate variation
      allocations = allocations.map(allocation => 
        allocation + (Math.random() - 0.5) * 6
      );
    }
    
    // Normalize to ensure sum is 100%
    const sum = allocations.reduce((total, curr) => total + curr, 0);
    allocations = allocations.map(allocation => (allocation / sum) * 100);
    
    return allocations.map(allocation => Math.round(allocation * 10) / 10);
  }

  private adjustReturnForRisk(baseReturn: number, riskTolerance: string): number {
    let adjustment = 1.0;
    
    switch (riskTolerance) {
      case 'Low':
        adjustment = 0.8; // More conservative returns
        break;
      case 'Medium':
        adjustment = 0.95;
        break;
      case 'High':
        adjustment = 1.15; // Higher expected returns
        break;
    }
    
    return Math.round((baseReturn * adjustment) * 10) / 10;
  }

  private calculatePortfolioReturn(recommendations: StockRecommendation[]): number {
    const weightedReturn = recommendations.reduce((total, stock) => {
      return total + (stock.expectedReturn * stock.allocation / 100);
    }, 0);
    
    return Math.round(weightedReturn * 10) / 10;
  }

  private calculateRiskScore(riskTolerance: string): number {
    switch (riskTolerance) {
      case 'Low': return 3.2;
      case 'Medium': return 5.8;
      case 'High': return 8.1;
      default: return 5.0;
    }
  }

  private generateProjectedGrowth(initialAmount: number, annualReturn: number, years: number): ProjectedGrowth[] {
    const projections: ProjectedGrowth[] = [];
    
    for (let year = 0; year <= years; year++) {
      const projectedValue = initialAmount * Math.pow(1 + (annualReturn / 100), year);
      projections.push({
        year,
        projectedValue: Math.round(projectedValue)
      });
    }
    
    return projections;
  }
}