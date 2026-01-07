import { Injectable } from "@angular/core";
import { Observable, of } from "rxjs";
import { catchError, map } from "rxjs/operators";
import { environment } from "../../environments/environment";
import { RateLimitInfo } from "../shared/models";
import { RateLimitApiService } from "./api/rate-limit-api.service";
import { LoggerService } from "./logger.service";

@Injectable({
  providedIn: "root",
})
export class RateLimitService {
  private readonly STORAGE_KEY = "portfolio_rate_limit";

  constructor(
    private rateLimitApiService: RateLimitApiService,
    private logger: LoggerService
  ) {}

  /**
   * Generate browser fingerprint for rate limiting
   */
  private generateFingerprint(): string {
    const userAgent = navigator.userAgent;
    const language = navigator.language;
    const platform = navigator.platform;
    const screenResolution = `${screen.width}x${screen.height}`;
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    const fingerprint = `${userAgent}_${language}_${platform}_${screenResolution}_${timezone}`;

    // Simple hash function
    let hash = 0;
    for (let i = 0; i < fingerprint.length; i++) {
      const char = fingerprint.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }

    return Math.abs(hash).toString(36);
  }

  /**
   * Check if user has exceeded rate limit
   * Calls BFF which checks Firebase Firestore
   */
  checkRateLimit(): Observable<{
    allowed: boolean;
    attemptsRemaining: number;
    rateLimitInfo: RateLimitInfo;
  }> {
    const fingerprint = this.generateFingerprint();
    this.logger.debug(
      "RateLimitService: Checking rate limit for fingerprint",
      fingerprint
    );

    // In mock mode, use localStorage (no BFF needed)
    if (environment.features.useMockData) {
      this.logger.debug("RateLimitService: Mock mode - using localStorage");
      return of(this.getFallbackRateLimit(fingerprint));
    }

    // Call BFF to check rate limit
    return this.rateLimitApiService.checkRateLimit(fingerprint).pipe(
      map((response) => {
        if (response.success && response.data) {
          const data = response.data;

          const rateLimitInfo: RateLimitInfo = {
            attempts: data.attemptsUsed,
            maxAttempts: data.attemptsUsed + data.attemptsRemaining,
            lastAttempt: new Date(data.resetAt),
            fingerprint,
          };

          // Also store in localStorage for backup
          this.saveToLocalStorage(rateLimitInfo);

          this.logger.info("RateLimitService: Rate limit check complete", {
            allowed: data.allowed,
            attemptsRemaining: data.attemptsRemaining,
          });

          return {
            allowed: data.allowed,
            attemptsRemaining: data.attemptsRemaining,
            rateLimitInfo,
          };
        } else {
          this.logger.warn(
            "RateLimitService: BFF returned unsuccessful response"
          );
          // Fallback to localStorage
          return this.getFallbackRateLimit(fingerprint);
        }
      }),
      catchError((error) => {
        this.logger.error(
          "RateLimitService: Error checking rate limit, using fallback",
          error
        );
        return of(this.getFallbackRateLimit(fingerprint));
      })
    );
  }

  /**
   * Increment attempt counter
   */
  incrementAttempt(): Observable<void> {
    const fingerprint = this.generateFingerprint();
    this.logger.debug(
      "RateLimitService: Incrementing attempt for fingerprint",
      fingerprint
    );

    // In mock mode, increment localStorage (no BFF needed)
    if (environment.features.useMockData) {
      this.logger.debug(
        "RateLimitService: Mock mode - incrementing localStorage"
      );

      const stored = this.getFromLocalStorage();
      if (stored) {
        stored.attempts += 1;
        stored.lastAttempt = new Date();
        this.saveToLocalStorage(stored);
        this.logger.debug("RateLimitService: Incremented to", stored.attempts);
      }

      return of(void 0);
    }

    // Call BFF to increment
    return this.rateLimitApiService.incrementRateLimit(fingerprint).pipe(
      map(() => {
        this.logger.info("RateLimitService: Attempt incremented successfully");
        return void 0;
      }),
      catchError((error) => {
        this.logger.error(
          "RateLimitService: Error incrementing attempt",
          error
        );
        // Still allow the operation to continue
        return of(void 0);
      })
    );
  }

  /**
   * Get fallback rate limit from localStorage
   */
  private getFallbackRateLimit(fingerprint: string): {
    allowed: boolean;
    attemptsRemaining: number;
    rateLimitInfo: RateLimitInfo;
  } {
    const stored = this.getFromLocalStorage();

    if (stored) {
      const allowed = stored.attempts < stored.maxAttempts;
      const attemptsRemaining = Math.max(
        0,
        stored.maxAttempts - stored.attempts
      );

      return { allowed, attemptsRemaining, rateLimitInfo: stored };
    }

    // Default fallback - save to localStorage
    const defaultInfo: RateLimitInfo = {
      attempts: 0,
      maxAttempts: 2,
      lastAttempt: new Date(),
      fingerprint,
    };

    this.saveToLocalStorage(defaultInfo);

    return {
      allowed: true,
      attemptsRemaining: 2,
      rateLimitInfo: defaultInfo,
    };
  }

  /**
   * Save to localStorage
   */
  private saveToLocalStorage(info: RateLimitInfo): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(info));
    } catch (error) {
      this.logger.warn(
        "RateLimitService: Failed to save to localStorage",
        error
      );
    }
  }

  /**
   * Get from localStorage
   */
  private getFromLocalStorage(): RateLimitInfo | null {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          ...parsed,
          lastAttempt: new Date(parsed.lastAttempt),
        };
      }
    } catch (error) {
      this.logger.warn(
        "RateLimitService: Failed to read from localStorage",
        error
      );
    }
    return null;
  }

  /**
   * Reset rate limit (for testing)
   */
  resetRateLimit(): Observable<void> {
    this.logger.debug("RateLimitService: Resetting rate limit");
    localStorage.removeItem(this.STORAGE_KEY);
    return of(void 0);
  }
}
