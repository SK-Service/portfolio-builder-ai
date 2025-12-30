// portfolio-builder-ai/frontend/src/app/shared/models/api-contracts.ts

// API Request/Response contracts for BFF communication

// ============================================
// Portfolio Generation
// ============================================

export interface GeneratePortfolioRequest {
  riskTolerance: "Low" | "Medium" | "High";
  investmentHorizonYears: number;
  country: Country;
  investmentAmount: number;
  currency?: Currency; // Optional, derived from country if not provided
}

export interface GeneratePortfolioResponse {
  success: boolean;
  data?: PortfolioRecommendationDto;
  error?: ApiError;
}

export interface PortfolioRecommendationDto {
  recommendations: StockRecommendationDto[];
  totalExpectedReturn: number;
  riskScore: number;
  projectedGrowth: ProjectedGrowthDto[];
  generatedAt: string; // ISO date string
}

export interface StockRecommendationDto {
  symbol: string;
  companyName: string;
  allocation: number; // percentage
  expectedReturn: number; // percentage
  sector: string;
  country: string;
}

export interface ProjectedGrowthDto {
  year: number;
  projectedValue: number;
}

// ============================================
// Configuration
// ============================================

export interface GetConfigRequest {
  // No body needed
}

export interface GetConfigResponse {
  success: boolean;
  data?: AppConfigDto;
  error?: ApiError;
}

export interface AppConfigDto {
  maxFreeAttempts: number; // From Firebase Firestore
  rateLimitWindowHours: number; // From Firebase Firestore
  supportedCountries: CountryConfigDto[];
  features: FeatureFlagsDto;
}

export interface CountryConfigDto {
  country: Country;
  currency: Currency;
  symbol: string;
  minInvestmentAmount: number;
  maxInvestmentAmount?: number; // Optional, future-proofing for when BFF provides this
}

export interface FeatureFlagsDto {
  maintenanceMode: boolean;
  newUserSignupEnabled: boolean;
}

// ============================================
// Rate Limiting
// ============================================

export interface CheckRateLimitRequest {
  fingerprint: string;
}

export interface CheckRateLimitResponse {
  success: boolean;
  data?: RateLimitCheckDto;
  error?: ApiError;
}

export interface RateLimitCheckDto {
  allowed: boolean;
  attemptsRemaining: number;
  attemptsUsed: number;
  resetAt: string; // ISO date string
}

export interface IncrementRateLimitRequest {
  fingerprint: string;
}

export interface IncrementRateLimitResponse {
  success: boolean;
  data?: {
    attemptsUsed: number;
    attemptsRemaining: number;
  };
  error?: ApiError;
}

// ============================================
// Common Types
// ============================================

export interface ApiError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

// Standard API response wrapper
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  metadata?: {
    requestId: string;
    duration: number; // milliseconds
  };
}

// Existing types (keep these for compatibility)
export type Country = "USA" | "EU" | "Canada" | "India";
export type Currency = "USD" | "EUR" | "CAD" | "INR";
export type RiskTolerance = "Low" | "Medium" | "High";
