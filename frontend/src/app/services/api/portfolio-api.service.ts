import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  ApiResponse,
  GeneratePortfolioRequest,
  PortfolioRecommendationDto
} from '../../shared/models/api-contracts';
import { ApiBaseService } from './api-base.service';

@Injectable({
  providedIn: 'root'
})
export class PortfolioApiService extends ApiBaseService {

  /**
   * Generate portfolio recommendations from BFF
   */
  generatePortfolio(request: GeneratePortfolioRequest): Observable<ApiResponse<PortfolioRecommendationDto>> {
    const endpoint = `${environment.api.endpoints.portfolio}/generate`;
    return this.post<PortfolioRecommendationDto>(endpoint, request);
  }
}