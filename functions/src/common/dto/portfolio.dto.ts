import {
  IsEnum,
  IsNumber,
  IsOptional,
  IsString,
  Max,
  Min,
} from 'class-validator';

export enum RiskTolerance {
  Low = 'Low',
  Medium = 'Medium',
  High = 'High',
}

export enum Country {
  USA = 'USA',
  EU = 'EU',
  Canada = 'Canada',
  India = 'India',
}

export enum Currency {
  USD = 'USD',
  EUR = 'EUR',
  CAD = 'CAD',
  INR = 'INR',
}

export class GeneratePortfolioRequestDto {
  @IsEnum(RiskTolerance)
  riskTolerance: RiskTolerance;

  @IsNumber()
  @Min(1)
  @Max(50)
  investmentHorizonYears: number;

  @IsEnum(Country)
  country: Country;

  @IsNumber()
  @Min(100)
  investmentAmount: number;

  @IsEnum(Currency)
  @IsOptional()
  currency?: Currency;
}

export class StockRecommendationDto {
  @IsString()
  symbol: string;

  @IsString()
  companyName: string;

  @IsNumber()
  allocation: number;

  @IsNumber()
  expectedReturn: number;

  @IsString()
  sector: string;

  @IsString()
  country: string;
}

export class ProjectedGrowthDto {
  @IsNumber()
  year: number;

  @IsNumber()
  projectedValue: number;
}

export class PortfolioRecommendationDto {
  recommendations: StockRecommendationDto[];
  totalExpectedReturn: number;
  riskScore: number;
  projectedGrowth: ProjectedGrowthDto[];
  generatedAt: string;
  error?: string; // For error handling (Option C)
}
