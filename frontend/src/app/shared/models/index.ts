// portfolio-builder-ai/shared/types/index.ts

export interface RiskAssessment {
  riskTolerance: RiskTolerance;
  investmentHorizonYears: number;
  country: Country;
  investmentAmount: number;
  currency: Currency;
}

export type RiskTolerance = 'Low' | 'Medium' | 'High';

export type Country = 'USA' | 'EU' | 'Canada' | 'India';

export type Currency = 'USD' | 'EUR' | 'CAD' | 'INR';

export interface CountryConfig {
  country: Country;
  currency: Currency;
  symbol: string;
}

export interface StockRecommendation {
  symbol: string;
  companyName: string;
  allocation: number; // percentage
  expectedReturn: number;
  sector: string;
  country: Country;
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
  fingerprint: string; // IP + UserAgent hash
}

export interface AppConfig {
  maxFreeAttempts: number;
  rateLimitWindowHours: number;
  supportedCountries: CountryConfig[];
}

export const COUNTRY_CONFIGS: CountryConfig[] = [
  { country: 'USA', currency: 'USD', symbol: '$' },
  { country: 'EU', currency: 'EUR', symbol: '€' },
  { country: 'Canada', currency: 'CAD', symbol: 'C$' },
  { country: 'India', currency: 'INR', symbol: '₹' }
];

export const RISK_TOLERANCE_OPTIONS: RiskTolerance[] = ['Low', 'Medium', 'High'];