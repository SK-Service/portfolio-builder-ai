import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse, AppConfigDto } from '../../shared/models/api-contracts';
import { ApiBaseService } from './api-base.service';

@Injectable({
  providedIn: 'root'
})
export class ConfigApiService extends ApiBaseService {

  /**
   * Fetch application configuration from BFF
   */
  getConfig(): Observable<ApiResponse<AppConfigDto>> {
    const endpoint = environment.api.endpoints.config;
    return this.get<AppConfigDto>(endpoint);
  }
}