import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, throwError, TimeoutError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { ApiError, ApiResponse } from '../../shared/models/api-contracts';

@Injectable({
  providedIn: 'root'
})
export class ApiBaseService {
  protected readonly baseUrl = environment.api.baseUrl;
  protected readonly defaultTimeout = environment.api.timeout;
  protected readonly retryAttempts = environment.api.retryAttempts;

  constructor(protected http: HttpClient) {}

  /**
   * GET request with error handling
   */
  protected get<T>(endpoint: string): Observable<ApiResponse<T>> {
    const url = this.buildUrl(endpoint);
    const headers = this.buildHeaders();

    return this.http.get<ApiResponse<T>>(url, { headers }).pipe(
      catchError((error: any) => this.handleError(error))
    );
  }

  /**
   * POST request with error handling
   */
  protected post<T>(endpoint: string, body: any): Observable<ApiResponse<T>> {
    const url = this.buildUrl(endpoint);
    const headers = this.buildHeaders();

    return this.http.post<ApiResponse<T>>(url, body, { headers }).pipe(
      catchError((error: any) => this.handleError(error))
    );
  }

  /**
   * PUT request with error handling
   */
  protected put<T>(endpoint: string, body: any): Observable<ApiResponse<T>> {
    const url = this.buildUrl(endpoint);
    const headers = this.buildHeaders();

    return this.http.put<ApiResponse<T>>(url, body, { headers }).pipe(
      catchError((error: any) => this.handleError(error))
    );
  }

  /**
   * DELETE request with error handling
   */
  protected delete<T>(endpoint: string): Observable<ApiResponse<T>> {
    const url = this.buildUrl(endpoint);
    const headers = this.buildHeaders();

    return this.http.delete<ApiResponse<T>>(url, { headers }).pipe(
      catchError((error: any) => this.handleError(error))
    );
  }

  /**
   * Build full URL from endpoint
   */
  private buildUrl(endpoint: string): string {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.substring(1) : endpoint;
    return `${this.baseUrl}/${cleanEndpoint}`;
  }

  /**
   * Build HTTP headers with security key
   */
  private buildHeaders(): HttpHeaders {
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'X-Portfolio-App-Key': environment.security.appKey,
      'X-Requested-With': 'XMLHttpRequest'
    });
  }

  /**
   * Centralized error handling
   */
  private handleError(error: HttpErrorResponse | TimeoutError | any): Observable<never> {
    let apiError: ApiError;

    if (error instanceof TimeoutError) {
      apiError = {
        code: 'TIMEOUT',
        message: 'Request timed out. Please try again.',
        timestamp: new Date().toISOString()
      };
    } else if (error.error instanceof ErrorEvent) {
      // Client-side error
      apiError = {
        code: 'CLIENT_ERROR',
        message: error.error.message,
        timestamp: new Date().toISOString()
      };
    } else if (error instanceof HttpErrorResponse) {
      // Server-side error
      apiError = {
        code: error.error?.code || `HTTP_${error.status}`,
        message: error.error?.message || this.getDefaultErrorMessage(error.status),
        details: error.error?.details,
        timestamp: new Date().toISOString()
      };
    } else {
      // Unknown error
      apiError = {
        code: 'UNKNOWN_ERROR',
        message: 'An unexpected error occurred.',
        details: error,
        timestamp: new Date().toISOString()
      };
    }

    console.error('API Error:', apiError);
    return throwError(() => apiError);
  }

  /**
   * Get user-friendly error message based on HTTP status
   */
  private getDefaultErrorMessage(status: number): string {
    switch (status) {
      case 400:
        return 'Invalid request. Please check your input.';
      case 401:
        return 'Unauthorized. Please log in again.';
      case 403:
        return 'Access forbidden. You do not have permission.';
      case 404:
        return 'Resource not found.';
      case 429:
        return 'Too many requests. Please try again later.';
      case 500:
        return 'Server error. Please try again later.';
      case 503:
        return 'Service unavailable. Please try again later.';
      default:
        return 'An unexpected error occurred. Please try again.';
    }
  }
}