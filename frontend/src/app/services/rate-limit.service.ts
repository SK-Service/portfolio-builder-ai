// portfolio-builder-ai/frontend/src/app/services/rate-limit.service.ts

import { Injectable } from '@angular/core';
import { Firestore, doc, getDoc, setDoc } from '@angular/fire/firestore';
import { Observable, from, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { RateLimitInfo } from '../shared/models';

@Injectable({
  providedIn: 'root'
})
export class RateLimitService {
  private readonly STORAGE_KEY = 'portfolio_rate_limit';
  private readonly COLLECTION_NAME = 'rate_limits';

  constructor(private firestore: Firestore) {}

  /**
   * Generates a fingerprint based on IP approximation and UserAgent
   * Note: We can't get real IP from browser, so we use available browser fingerprinting
   */
  private generateFingerprint(): string {
    const userAgent = navigator.userAgent;
    const language = navigator.language;
    const platform = navigator.platform;
    const screenResolution = `${screen.width}x${screen.height}`;
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    // Create a semi-unique fingerprint
    const fingerprint = `${userAgent}_${language}_${platform}_${screenResolution}_${timezone}`;
    
    // Simple hash function
    let hash = 0;
    for (let i = 0; i < fingerprint.length; i++) {
      const char = fingerprint.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    
    return Math.abs(hash).toString(36);
  }

  /**
   * Checks if user has exceeded rate limit
   */
  checkRateLimit(): Observable<{ allowed: boolean; attemptsRemaining: number; rateLimitInfo: RateLimitInfo }> {
    const fingerprint = this.generateFingerprint();
    
    return from(this.getRateLimitFromFirestore(fingerprint)).pipe(
      map(firestoreData => {
        const localData = this.getRateLimitFromLocalStorage();
        
        // Use the more restrictive of local or Firestore data
        const rateLimitInfo = this.mergeRateLimitData(localData, firestoreData, fingerprint);
        
        const allowed = rateLimitInfo.attempts < rateLimitInfo.maxAttempts;
        const attemptsRemaining = Math.max(0, rateLimitInfo.maxAttempts - rateLimitInfo.attempts);
        
        return { allowed, attemptsRemaining, rateLimitInfo };
      }),
      catchError(error => {
        console.warn('Error checking rate limit from Firestore, using local storage only:', error);
        const localData = this.getRateLimitFromLocalStorage();
        const rateLimitInfo = localData || this.createDefaultRateLimitInfo(fingerprint);
        
        const allowed = rateLimitInfo.attempts < rateLimitInfo.maxAttempts;
        const attemptsRemaining = Math.max(0, rateLimitInfo.maxAttempts - rateLimitInfo.attempts);
        
        return of({ allowed, attemptsRemaining, rateLimitInfo });
      })
    );
  }

  /**
   * Increments the attempt counter
   */
  incrementAttempt(): Observable<void> {
    const fingerprint = this.generateFingerprint();
    
    return this.checkRateLimit().pipe(
      map(({ rateLimitInfo }) => {
        const updatedInfo: RateLimitInfo = {
          ...rateLimitInfo,
          attempts: rateLimitInfo.attempts + 1,
          lastAttempt: new Date()
        };
        
        // Update both local storage and Firestore
        this.saveRateLimitToLocalStorage(updatedInfo);
        this.saveRateLimitToFirestore(updatedInfo).catch(error => {
          console.warn('Failed to save rate limit to Firestore:', error);
        });
      })
    );
  }

  /**
   * Gets rate limit data from localStorage
   */
  private getRateLimitFromLocalStorage(): RateLimitInfo | null {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          ...parsed,
          lastAttempt: new Date(parsed.lastAttempt)
        };
      }
    } catch (error) {
      console.warn('Error reading rate limit from localStorage:', error);
    }
    return null;
  }

  /**
   * Saves rate limit data to localStorage
   */
  private saveRateLimitToLocalStorage(rateLimitInfo: RateLimitInfo): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(rateLimitInfo));
    } catch (error) {
      console.warn('Error saving rate limit to localStorage:', error);
    }
  }

  /**
   * Gets rate limit data from Firestore
   */
  private async getRateLimitFromFirestore(fingerprint: string): Promise<RateLimitInfo | null> {
    try {
      const docRef = doc(this.firestore, this.COLLECTION_NAME, fingerprint);
      const docSnap = await getDoc(docRef);
      
      if (docSnap.exists()) {
        const data = docSnap.data();
        return {
          attempts: data['attempts'] || 0,
          maxAttempts: data['maxAttempts'] || 2,
          lastAttempt: data['lastAttempt']?.toDate() || new Date(),
          fingerprint: fingerprint
        };
      }
    } catch (error) {
      console.warn('Error reading from Firestore:', error);
    }
    return null;
  }

  /**
   * Saves rate limit data to Firestore
   */
  private async saveRateLimitToFirestore(rateLimitInfo: RateLimitInfo): Promise<void> {
    try {
      const docRef = doc(this.firestore, this.COLLECTION_NAME, rateLimitInfo.fingerprint);
      await setDoc(docRef, {
        attempts: rateLimitInfo.attempts,
        maxAttempts: rateLimitInfo.maxAttempts,
        lastAttempt: rateLimitInfo.lastAttempt,
        fingerprint: rateLimitInfo.fingerprint,
        updatedAt: new Date()
      }, { merge: true });
    } catch (error) {
      console.warn('Error saving to Firestore:', error);
      throw error;
    }
  }

  /**
   * Creates default rate limit info
   */
  private createDefaultRateLimitInfo(fingerprint: string): RateLimitInfo {
    return {
      attempts: 0,
      maxAttempts: 2, // Default, will be overridden by config service
      lastAttempt: new Date(),
      fingerprint: fingerprint
    };
  }

  /**
   * Merges local and Firestore rate limit data, taking the more restrictive values
   */
  private mergeRateLimitData(
    localData: RateLimitInfo | null, 
    firestoreData: RateLimitInfo | null,
    fingerprint: string
  ): RateLimitInfo {
    if (!localData && !firestoreData) {
      return this.createDefaultRateLimitInfo(fingerprint);
    }
    
    if (!localData) return firestoreData!;
    if (!firestoreData) return localData;
    
    // Take the higher attempt count (more restrictive)
    return {
      attempts: Math.max(localData.attempts, firestoreData.attempts),
      maxAttempts: localData.maxAttempts,
      lastAttempt: localData.lastAttempt > firestoreData.lastAttempt ? localData.lastAttempt : firestoreData.lastAttempt,
      fingerprint: fingerprint
    };
  }

  /**
   * Resets rate limit (for testing or admin purposes)
   */
  resetRateLimit(): Observable<void> {
    const fingerprint = this.generateFingerprint();
    const resetInfo: RateLimitInfo = {
      attempts: 0,
      maxAttempts: 2,
      lastAttempt: new Date(),
      fingerprint: fingerprint
    };

    this.saveRateLimitToLocalStorage(resetInfo);
    
    return from(this.saveRateLimitToFirestore(resetInfo)).pipe(
      map(() => void 0),
      catchError(error => {
        console.warn('Failed to reset rate limit in Firestore:', error);
        return of(void 0);
      })
    );
  }
}