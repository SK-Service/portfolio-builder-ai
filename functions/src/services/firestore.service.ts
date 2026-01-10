import { Injectable, OnModuleInit } from '@nestjs/common';
import { AppConfigDto } from '../common/dto/config.dto';
import { RateLimitResponseDto } from '../common/dto/rate-limit.dto';
import { environment } from '../config/environment';
import { getFirestore } from '../config/firebase.config';

interface RateLimitData {
  fingerprint: string;
  attempts: number;
  maxAttempts: number;
  lastAttempt: string;
  resetAt: string;
  createdAt: string;
  updatedAt: string;
}

@Injectable()
export class FirestoreService implements OnModuleInit {
  private db: FirebaseFirestore.Firestore;

  onModuleInit() {
    this.db = getFirestore();
    console.log('FirestoreService initialized');
  }

  async getAppConfig(): Promise<AppConfigDto | null> {
    try {
      const docRef = this.db.collection('app_config').doc('default');
      const doc = await docRef.get();

      if (!doc.exists) {
        console.warn('App config not found in Firestore');
        return null;
      }

      return doc.data() as AppConfigDto;
    } catch (error) {
      console.error('Error fetching app config from Firestore:', error);
      throw error;
    }
  }

  async getRateLimit(
    fingerprint: string,
  ): Promise<RateLimitResponseDto | null> {
    try {
      const docRef = this.db.collection('rate_limits').doc(fingerprint);
      const doc = await docRef.get();

      if (!doc.exists) {
        return null;
      }

      const data = doc.data() as RateLimitData | undefined;

      if (!data) {
        return null;
      }

      // Check if reset time has passed
      const now = new Date();
      const resetAt = new Date(data.resetAt);

      if (now > resetAt) {
        // Reset period has passed - reset the attempts
        console.log(
          `Rate limit reset for fingerprint: ${fingerprint.substring(0, 10)}...`,
        );
        await this.resetRateLimitAttempts(docRef, data.maxAttempts);

        return {
          allowed: true,
          attemptsRemaining: data.maxAttempts,
          attemptsUsed: 0,
          resetAt: data.resetAt, // Will be updated on next increment
        };
      }

      return {
        allowed: data.attempts < data.maxAttempts,
        attemptsRemaining: Math.max(0, data.maxAttempts - data.attempts),
        attemptsUsed: data.attempts,
        resetAt: data.resetAt,
      };
    } catch (error) {
      console.error('Error fetching rate limit from Firestore:', error);
      throw error;
    }
  }

  /**
   * Reset rate limit attempts when reset period has passed
   */
  private async resetRateLimitAttempts(
    docRef: FirebaseFirestore.DocumentReference,
    maxAttempts: number,
  ): Promise<void> {
    const now = new Date();

    await docRef.update({
      attempts: 0,
      maxAttempts,
      updatedAt: now.toISOString(),
    });
  }

  async incrementRateLimit(
    fingerprint: string,
    maxAttempts: number,
  ): Promise<RateLimitResponseDto> {
    try {
      const docRef = this.db.collection('rate_limits').doc(fingerprint);
      const doc = await docRef.get();

      const now = new Date();
      const windowHours = environment.rateLimit.windowHours;
      const resetAt = new Date(now.getTime() + windowHours * 60 * 60 * 1000);

      if (!doc.exists) {
        // New fingerprint - create new record
        const newData: RateLimitData = {
          fingerprint,
          attempts: 1,
          maxAttempts,
          lastAttempt: now.toISOString(),
          resetAt: resetAt.toISOString(),
          createdAt: now.toISOString(),
          updatedAt: now.toISOString(),
        };

        await docRef.set(newData);

        return {
          allowed: true,
          attemptsRemaining: maxAttempts - 1,
          attemptsUsed: 1,
          resetAt: resetAt.toISOString(),
        };
      }

      const data = doc.data() as RateLimitData | undefined;

      if (!data) {
        throw new Error('Rate limit data is undefined');
      }

      // Check if reset time has passed
      const existingResetAt = new Date(data.resetAt);

      if (now > existingResetAt) {
        // Reset period has passed - reset attempts and set new window
        console.log(
          `Rate limit reset on increment for fingerprint: ${fingerprint.substring(0, 10)}...`,
        );

        await docRef.update({
          attempts: 1,
          maxAttempts,
          lastAttempt: now.toISOString(),
          resetAt: resetAt.toISOString(),
          updatedAt: now.toISOString(),
        });

        return {
          allowed: true,
          attemptsRemaining: maxAttempts - 1,
          attemptsUsed: 1,
          resetAt: resetAt.toISOString(),
        };
      }

      // Within current window - increment attempts and update resetAt (rolling window)
      const newAttempts = data.attempts + 1;

      await docRef.update({
        attempts: newAttempts,
        lastAttempt: now.toISOString(),
        resetAt: resetAt.toISOString(), // Rolling window: reset from last attempt
        updatedAt: now.toISOString(),
      });

      return {
        allowed: newAttempts < maxAttempts,
        attemptsRemaining: Math.max(0, maxAttempts - newAttempts),
        attemptsUsed: newAttempts,
        resetAt: resetAt.toISOString(),
      };
    } catch (error) {
      console.error('Error incrementing rate limit in Firestore:', error);
      throw error;
    }
  }
}
