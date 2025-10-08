// portfolio-builder-ai/frontend/src/app/services/config.service.ts

import { Injectable } from '@angular/core';
import { Firestore, doc, getDoc } from '@angular/fire/firestore';
import { BehaviorSubject, Observable, from, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { AppConfig } from '../shared/models';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private readonly CONFIG_COLLECTION = 'app_config';
  private readonly CONFIG_DOC_ID = 'default';
  
  private configSubject = new BehaviorSubject<AppConfig | null>(null);
  public config$ = this.configSubject.asObservable();

  private defaultConfig: AppConfig = {
    maxFreeAttempts: environment.rateLimit.defaultMaxAttempts,
    rateLimitWindowHours: environment.rateLimit.windowHours,
    supportedCountries: [
      { country: 'USA', currency: 'USD', symbol: '$' },
      { country: 'EU', currency: 'EUR', symbol: '€' },
      { country: 'Canada', currency: 'CAD', symbol: 'C$' },
      { country: 'India', currency: 'INR', symbol: '₹' }
    ]
  };

  constructor(private firestore: Firestore) {
    this.loadConfig();
  }

  /**
   * Loads configuration from Firebase or uses defaults
   */
  private loadConfig(): void {
    this.getConfigFromFirestore().subscribe({
      next: (config) => {
        this.configSubject.next(config);
      },
      error: (error) => {
        console.warn('Failed to load config from Firebase, using defaults:', error);
        this.configSubject.next(this.defaultConfig);
      }
    });
  }

  /**
   * Gets current configuration
   */
  getConfig(): AppConfig {
    const currentConfig = this.configSubject.value;
    return currentConfig || this.defaultConfig;
  }

  /**
   * Gets max free attempts from config
   */
  getMaxFreeAttempts(): number {
    return this.getConfig().maxFreeAttempts;
  }

  /**
   * Gets rate limit window in hours
   */
  getRateLimitWindowHours(): number {
    return this.getConfig().rateLimitWindowHours;
  }

  /**
   * Gets supported countries configuration
   */
  getSupportedCountries() {
    return this.getConfig().supportedCountries;
  }

  /**
   * Retrieves configuration from Firestore
   */
  private getConfigFromFirestore(): Observable<AppConfig> {
    const configDocRef = doc(this.firestore, this.CONFIG_COLLECTION, this.CONFIG_DOC_ID);
    
    return from(getDoc(configDocRef)).pipe(
      map(docSnap => {
        if (docSnap.exists()) {
          const data = docSnap.data();
          return {
            maxFreeAttempts: data['maxFreeAttempts'] || this.defaultConfig.maxFreeAttempts,
            rateLimitWindowHours: data['rateLimitWindowHours'] || this.defaultConfig.rateLimitWindowHours,
            supportedCountries: data['supportedCountries'] || this.defaultConfig.supportedCountries
          };
        } else {
          // Document doesn't exist, create it with default values
          this.createDefaultConfig();
          return this.defaultConfig;
        }
      }),
      catchError(error => {
        console.error('Error fetching config from Firestore:', error);
        return of(this.defaultConfig);
      })
    );
  }

  /**
   * Creates default configuration document in Firestore
   */
  private async createDefaultConfig(): Promise<void> {
    try {
      const configDocRef = doc(this.firestore, this.CONFIG_COLLECTION, this.CONFIG_DOC_ID);
      await import('@angular/fire/firestore').then(({ setDoc }) => 
        setDoc(configDocRef, {
          ...this.defaultConfig,
          createdAt: new Date(),
          updatedAt: new Date()
        })
      );
      console.log('Default config created in Firestore');
    } catch (error) {
      console.warn('Failed to create default config in Firestore:', error);
    }
  }

  /**
   * Refreshes configuration from Firebase
   */
  refreshConfig(): Observable<AppConfig> {
    return this.getConfigFromFirestore().pipe(
      tap(config => this.configSubject.next(config))
    );
  }

  /**
   * Checks if a feature is enabled
   */
  isFeatureEnabled(feature: keyof typeof environment.features): boolean {
    return environment.features[feature];
  }

  /**
   * Gets API configuration
   */
  getApiConfig() {
    return environment.api;
  }
}