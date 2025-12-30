// portfolio-builder-ai/frontend/src/app/shared/models/index.ts

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
  minInvestmentAmount: number;
  maxInvestmentAmount?: number; // Optional for backward compatibility with API
}

// ============================================
// Type Definitions
// ============================================

export type Country = "USA" | "EU" | "Canada" | "India";
export type Currency = "USD" | "EUR" | "CAD" | "INR";
export type RiskTolerance = "Low" | "Medium" | "High";

// Default max investment amounts per country (used when not provided by API)
export const DEFAULT_MAX_INVESTMENT: Record<Country, number> = {
  USA: 1000000,
  EU: 1000000,
  Canada: 1000000,
  India: 10000000,
};

export const COUNTRY_CONFIGS: CountryConfig[] = [
  {
    country: "USA",
    currency: "USD",
    symbol: "$",
    minInvestmentAmount: 5000,
    maxInvestmentAmount: 1000000,
  },
  {
    country: "EU",
    currency: "EUR",
    symbol: "€",
    minInvestmentAmount: 5000,
    maxInvestmentAmount: 1000000,
  },
  {
    country: "Canada",
    currency: "CAD",
    symbol: "C$",
    minInvestmentAmount: 5000,
    maxInvestmentAmount: 1000000,
  },
  {
    country: "India",
    currency: "INR",
    symbol: "₹",
    minInvestmentAmount: 20000,
    maxInvestmentAmount: 10000000,
  },
];

export const RISK_TOLERANCE_OPTIONS: RiskTolerance[] = [
  "Low",
  "Medium",
  "High",
];

// ============================================
// Export API Contracts (NEW)
// ============================================

export * from "./api-contracts";
