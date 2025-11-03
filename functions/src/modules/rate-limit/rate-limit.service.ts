import { Injectable } from '@nestjs/common';
import {
  CheckRateLimitRequestDto,
  IncrementRateLimitRequestDto,
  RateLimitResponseDto,
} from '../../common/dto/rate-limit.dto';
import { environment } from '../../config/environment';
import { FirestoreService } from '../../services/firestore.service';
import { mockRateLimitCheck } from '../../services/mocks/mock-data';

@Injectable()
export class RateLimitService {
  constructor(private readonly firestoreService: FirestoreService) {}

  async checkRateLimit(
    request: CheckRateLimitRequestDto,
  ): Promise<RateLimitResponseDto> {
    try {
      const rateLimit = await this.firestoreService.getRateLimit(
        request.fingerprint,
      );

      if (!rateLimit) {
        console.log(
          `New fingerprint: ${request.fingerprint.substring(0, 10)}...`,
        );
        return {
          allowed: true,
          attemptsRemaining: environment.rateLimit.maxAttemptsPerFingerprint,
          attemptsUsed: 0,
          resetAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
        };
      }

      console.log(
        `Rate limit check: ${request.fingerprint.substring(0, 10)}... - ${rateLimit.attemptsUsed}/${environment.rateLimit.maxAttemptsPerFingerprint} attempts`,
      );

      return rateLimit;
    } catch (error) {
      console.error('Error checking rate limit, falling back to mock:', error);
      return mockRateLimitCheck;
    }
  }

  async incrementRateLimit(
    request: IncrementRateLimitRequestDto,
  ): Promise<RateLimitResponseDto> {
    try {
      const result = await this.firestoreService.incrementRateLimit(
        request.fingerprint,
        environment.rateLimit.maxAttemptsPerFingerprint,
      );

      console.log(
        `Rate limit incremented: ${request.fingerprint.substring(0, 10)}... - ${result.attemptsUsed}/${environment.rateLimit.maxAttemptsPerFingerprint} attempts`,
      );

      return result;
    } catch (error) {
      console.error(
        'Error incrementing rate limit, falling back to mock:',
        error,
      );
      return {
        allowed: true,
        attemptsRemaining: 1,
        attemptsUsed: 1,
        resetAt: mockRateLimitCheck.resetAt,
      };
    }
  }
}
