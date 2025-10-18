// Export all model interfaces

// ============================================
// Existing Domain Models (keep these)
// ============================================

export interface RiskAssessment {
  riskTolerance: RiskTolerance;
  investmentHorizonYears: number;
  country: Country;
  investmentAmount: number;
  currency: Currency;
}

export interface StockRecommendation {
  symbol: string;
  companyName: string;
  allocation: number;
  expectedReturn: number;
  sector: string;
  country: string;
}

export interface PortfolioRecommendation {
  recommendations: StockRecommendation[];
  totalExpectedReturn: number;
  riskScore: number;
  projectedGrowth: ProjectedGrowth[];
}

export interface ProjectedGrowth {
  year: number;
  projectedValue: number;
}

export interface RateLimitInfo {
  attempts: number;
  maxAttempts: number;
  lastAttempt: Date;
  fingerprint: string;
}

export interface AppConfig {
  maxFreeAttempts: number;
  rateLimitWindowHours: number;
  supportedCountries: CountryConfig[];
}

export interface CountryConfig {
  country: Country;
  currency: Currency;
  symbol: string;
  minInvestmentAmount?: number;  // Optional for now
}

// ============================================
// Type Definitions
// ============================================

export type Country = 'USA' | 'EU' | 'Canada' | 'India';
export type Currency = 'USD' | 'EUR' | 'CAD' | 'INR';
export type RiskTolerance = 'Low' | 'Medium' | 'High';

export const COUNTRY_CONFIGS: CountryConfig[] = [
  { country: 'USA', currency: 'USD', symbol: '$', minInvestmentAmount: 100 },
  { country: 'EU', currency: 'EUR', symbol: '€', minInvestmentAmount: 100 },
  { country: 'Canada', currency: 'CAD', symbol: 'C$', minInvestmentAmount: 100 },
  { country: 'India', currency: 'INR', symbol: '₹', minInvestmentAmount: 5000 }
];

export const RISK_TOLERANCE_OPTIONS: RiskTolerance[] = ['Low', 'Medium', 'High'];

// ============================================
// Export API Contracts (NEW)
// ============================================

export * from './api-contracts';

