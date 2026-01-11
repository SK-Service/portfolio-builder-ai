// portfolio-builder-ai/frontend/src/app/services/portfolio-cache.service.ts

import { Injectable } from "@angular/core";
import { PortfolioRecommendation, RiskAssessment } from "../shared/models";
import { LoggerService } from "./logger.service";

interface CachedPortfolio {
  cacheKey: string;
  portfolio: PortfolioRecommendation;
  cachedAt: string;
}

@Injectable({
  providedIn: "root",
})
export class PortfolioCacheService {
  private readonly PORTFOLIO_CACHE_KEY = "portfolio_cache";
  private readonly CACHE_TTL_HOURS = 24;

  constructor(private logger: LoggerService) {}

  /**
   * Generate a cache key from risk assessment inputs
   * This ensures cache is only used when inputs are identical
   */
  generateCacheKey(assessment: RiskAssessment): string {
    return `${assessment.riskTolerance}_${assessment.investmentHorizonYears}_${assessment.country}_${assessment.investmentAmount}_${assessment.currency}`;
  }

  /**
   * Check if cache has expired based on TTL
   */
  private isCacheExpired(cachedAt: string): boolean {
    const cachedTime = new Date(cachedAt).getTime();
    const now = Date.now();
    const ttlMs = this.CACHE_TTL_HOURS * 60 * 60 * 1000;

    return now - cachedTime > ttlMs;
  }

  /**
   * Check if there's a cache hit for the given assessment
   */
  hasCacheHit(assessment: RiskAssessment): boolean {
    const currentCacheKey = this.generateCacheKey(assessment);
    const cachedData = this.getCachedPortfolio();

    if (cachedData && cachedData.cacheKey === currentCacheKey) {
      // Check TTL
      if (this.isCacheExpired(cachedData.cachedAt)) {
        this.logger.debug("PortfolioCacheService: Cache expired");
        return false;
      }
      this.logger.debug("PortfolioCacheService: Cache hit for assessment");
      return true;
    }

    this.logger.debug("PortfolioCacheService: Cache miss for assessment");
    return false;
  }

  /**
   * Get cached portfolio from sessionStorage
   */
  getCachedPortfolio(): CachedPortfolio | null {
    try {
      const stored = sessionStorage.getItem(this.PORTFOLIO_CACHE_KEY);
      if (stored) {
        return JSON.parse(stored) as CachedPortfolio;
      }
    } catch (error) {
      this.logger.warn("PortfolioCacheService: Error reading cache", error);
    }
    return null;
  }

  /**
   * Get cached portfolio if it matches the given assessment and is not expired
   */
  getPortfolioForAssessment(
    assessment: RiskAssessment
  ): PortfolioRecommendation | null {
    const currentCacheKey = this.generateCacheKey(assessment);
    const cachedData = this.getCachedPortfolio();

    if (cachedData && cachedData.cacheKey === currentCacheKey) {
      // Check TTL
      if (this.isCacheExpired(cachedData.cachedAt)) {
        this.logger.info(
          "PortfolioCacheService: Cache expired, returning null"
        );
        return null;
      }
      this.logger.info("PortfolioCacheService: Returning cached portfolio");
      return cachedData.portfolio;
    }

    return null;
  }

  /**
   * Save portfolio to sessionStorage cache
   */
  cachePortfolio(
    portfolio: PortfolioRecommendation,
    assessment: RiskAssessment
  ): void {
    try {
      const cacheData: CachedPortfolio = {
        cacheKey: this.generateCacheKey(assessment),
        portfolio: portfolio,
        cachedAt: new Date().toISOString(),
      };
      sessionStorage.setItem(
        this.PORTFOLIO_CACHE_KEY,
        JSON.stringify(cacheData)
      );
      this.logger.info("PortfolioCacheService: Portfolio cached successfully");
    } catch (error) {
      this.logger.warn("PortfolioCacheService: Error caching portfolio", error);
    }
  }

  /**
   * Clear the portfolio cache
   */
  clearCache(): void {
    sessionStorage.removeItem(this.PORTFOLIO_CACHE_KEY);
    this.logger.debug("PortfolioCacheService: Cache cleared");
  }
}
