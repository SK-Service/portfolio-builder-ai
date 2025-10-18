import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    ApiResponse,
    CheckRateLimitRequest,
    IncrementRateLimitRequest,
    RateLimitCheckDto
} from '../../shared/models/api-contracts';
import { ApiBaseService } from './api-base.service';

@Injectable({
  providedIn: 'root'
})
export class RateLimitApiService extends ApiBaseService {

  /**
   * Check rate limit status
   */
  checkRateLimit(fingerprint: string): Observable<ApiResponse<RateLimitCheckDto>> {
    const endpoint = `${environment.api.endpoints.rateLimit}/check`;
    const request: CheckRateLimitRequest = { fingerprint };
    return this.post<RateLimitCheckDto>(endpoint, request);
  }

  /**
   * Increment rate limit counter
   */
  incrementRateLimit(fingerprint: string): Observable<ApiResponse<any>> {
    const endpoint = `${environment.api.endpoints.rateLimit}/increment`;
    const request: IncrementRateLimitRequest = { fingerprint };
    return this.post<any>(endpoint, request);
  }
}