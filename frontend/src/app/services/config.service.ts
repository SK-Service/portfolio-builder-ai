import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { AppConfig, COUNTRY_CONFIGS, CountryConfig } from '../shared/models';
import { ConfigApiService } from './api/config-api.service';
import { LoggerService } from './logger.service';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private configSubject = new BehaviorSubject<AppConfig | null>(null);
  public config$: Observable<AppConfig | null> = this.configSubject.asObservable();

  // Default config (used only as fallback if BFF fails)
  private readonly defaultConfig: AppConfig = {
    maxFreeAttempts: 2,
    rateLimitWindowHours: 24,
    supportedCountries: COUNTRY_CONFIGS
  };

  constructor(
    private configApiService: ConfigApiService,
    private logger: LoggerService
  ) {
    this.loadConfig();
  }

  /**
   * Load configuration from BFF on service initialization
   */
  private loadConfig(): void {
    this.logger.debug('ConfigService: Loading configuration from BFF');

    if (environment.features.useMockData) {
      // In mock mode, use default config immediately
      this.logger.debug('ConfigService: Using mock configuration');
      this.configSubject.next(this.defaultConfig);
      return;
    }

    // Call BFF to get config (which fetches from Firebase Firestore)
    this.configApiService.getConfig().subscribe({
      next: (response) => {
        if (response.success && response.data) {
          this.logger.info('ConfigService: Configuration loaded successfully', response.data);
          
          const config: AppConfig = {
            maxFreeAttempts: response.data.maxFreeAttempts,
            rateLimitWindowHours: response.data.rateLimitWindowHours,
            supportedCountries: response.data.supportedCountries || COUNTRY_CONFIGS
          };
          
          this.configSubject.next(config);
        } else {
          this.logger.warn('ConfigService: BFF returned unsuccessful response, using defaults');
          this.configSubject.next(this.defaultConfig);
        }
      },
      error: (error) => {
        this.logger.error('ConfigService: Failed to load config from BFF, using defaults', error);
        this.configSubject.next(this.defaultConfig);
      }
    });
  }

  /**
   * Get current configuration (synchronous)
   */
  getConfig(): AppConfig {
    return this.configSubject.value || this.defaultConfig;
  }

  /**
   * Get max free attempts
   */
  getMaxFreeAttempts(): number {
    return this.getConfig().maxFreeAttempts;
  }

  /**
   * Get rate limit window in hours
   */
  getRateLimitWindowHours(): number {
    return this.getConfig().rateLimitWindowHours;
  }

  /**
   * Get supported countries
   */
  getSupportedCountries(): CountryConfig[] {
    return this.getConfig().supportedCountries;
  }

  /**
   * Refresh configuration from BFF
   */
  refreshConfig(): Observable<AppConfig> {
    this.logger.debug('ConfigService: Refreshing configuration');

    return this.configApiService.getConfig().pipe(
      map(response => {
        if (response.success && response.data) {
          const config: AppConfig = {
            maxFreeAttempts: response.data.maxFreeAttempts,
            rateLimitWindowHours: response.data.rateLimitWindowHours,
            supportedCountries: response.data.supportedCountries || COUNTRY_CONFIGS
          };
          this.configSubject.next(config);
          return config;
        }
        return this.defaultConfig;
      }),
      catchError(error => {
        this.logger.error('ConfigService: Refresh failed', error);
        return of(this.defaultConfig);
      })
    );
  }

  /**
   * Check if a feature is enabled
   */
  isFeatureEnabled(feature: keyof typeof environment.features): boolean {
    return environment.features[feature];
  }

  /**
   * Get API configuration
   */
  getApiConfig() {
    return environment.api;
  }
}