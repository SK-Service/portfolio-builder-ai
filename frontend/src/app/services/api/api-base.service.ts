import {
  HttpClient,
  HttpErrorResponse,
  HttpHeaders,
} from "@angular/common/http";
import { Injectable } from "@angular/core";
import { Observable, throwError, TimeoutError } from "rxjs";
import { catchError, tap } from "rxjs/operators";
import { environment } from "../../../environments/environment";
import { ApiError, ApiResponse } from "../../shared/models/api-contracts";

@Injectable({
  providedIn: "root",
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

    console.log("[API] GET Request:", {
      url,
      headers: this.headersToObject(headers),
    });

    return this.http.get<ApiResponse<T>>(url, { headers }).pipe(
      tap((response) => console.log("[API] GET Response:", { url, response })),
      catchError((error: any) => this.handleError(error, "GET", url))
    );
  }

  /**
   * POST request with error handling
   */
  protected post<T>(endpoint: string, body: any): Observable<ApiResponse<T>> {
    const url = this.buildUrl(endpoint);
    const headers = this.buildHeaders();

    console.log("[API] POST Request:", {
      url,
      headers: this.headersToObject(headers),
      body,
    });

    return this.http.post<ApiResponse<T>>(url, body, { headers }).pipe(
      tap((response) => console.log("[API] POST Response:", { url, response })),
      catchError((error: any) => this.handleError(error, "POST", url))
    );
  }

  /**
   * PUT request with error handling
   */
  protected put<T>(endpoint: string, body: any): Observable<ApiResponse<T>> {
    const url = this.buildUrl(endpoint);
    const headers = this.buildHeaders();

    console.log("[API] PUT Request:", {
      url,
      headers: this.headersToObject(headers),
      body,
    });

    return this.http.put<ApiResponse<T>>(url, body, { headers }).pipe(
      tap((response) => console.log("[API] PUT Response:", { url, response })),
      catchError((error: any) => this.handleError(error, "PUT", url))
    );
  }

  /**
   * DELETE request with error handling
   */
  protected delete<T>(endpoint: string): Observable<ApiResponse<T>> {
    const url = this.buildUrl(endpoint);
    const headers = this.buildHeaders();

    console.log("[API] DELETE Request:", {
      url,
      headers: this.headersToObject(headers),
    });

    return this.http.delete<ApiResponse<T>>(url, { headers }).pipe(
      tap((response) =>
        console.log("[API] DELETE Response:", { url, response })
      ),
      catchError((error: any) => this.handleError(error, "DELETE", url))
    );
  }

  /**
   * Build full URL from endpoint
   */
  private buildUrl(endpoint: string): string {
    const cleanEndpoint = endpoint.startsWith("/")
      ? endpoint.substring(1)
      : endpoint;
    const fullUrl = `${this.baseUrl}/${cleanEndpoint}`;
    console.log("[API] Built URL:", {
      baseUrl: this.baseUrl,
      endpoint,
      fullUrl,
    });
    return fullUrl;
  }

  /**
   * Build HTTP headers with security key
   */
  private buildHeaders(): HttpHeaders {
    return new HttpHeaders({
      "Content-Type": "application/json",
      "X-Portfolio-App-Key": environment.security.appKey,
      "X-Requested-With": "XMLHttpRequest",
    });
  }

  /**
   * Convert HttpHeaders to plain object for logging
   */
  private headersToObject(headers: HttpHeaders): Record<string, string> {
    const obj: Record<string, string> = {};
    headers.keys().forEach((key) => {
      const value = headers.get(key);
      if (value) {
        // Mask sensitive values
        if (
          key.toLowerCase().includes("key") ||
          key.toLowerCase().includes("token")
        ) {
          obj[key] = value.substring(0, 4) + "****";
        } else {
          obj[key] = value;
        }
      }
    });
    return obj;
  }

  /**
   * Centralized error handling
   */
  private handleError(
    error: HttpErrorResponse | TimeoutError | any,
    method: string,
    url: string
  ): Observable<never> {
    let apiError: ApiError;

    console.error(`[API] ${method} Error:`, { url, error });

    if (error instanceof TimeoutError) {
      apiError = {
        code: "TIMEOUT",
        message: "Request timed out. Please try again.",
        timestamp: new Date().toISOString(),
      };
    } else if (error.error instanceof ErrorEvent) {
      // Client-side error
      apiError = {
        code: "CLIENT_ERROR",
        message: error.error.message,
        timestamp: new Date().toISOString(),
      };
    } else if (error instanceof HttpErrorResponse) {
      // Server-side error
      console.error(`[API] HTTP ${error.status} from ${url}:`, {
        status: error.status,
        statusText: error.statusText,
        errorBody: error.error,
        headers: error.headers?.keys(),
      });

      apiError = {
        code: error.error?.code || `HTTP_${error.status}`,
        message:
          error.error?.message || this.getDefaultErrorMessage(error.status),
        details: error.error?.details,
        timestamp: new Date().toISOString(),
      };
    } else {
      // Unknown error
      apiError = {
        code: "UNKNOWN_ERROR",
        message: "An unexpected error occurred.",
        details: error,
        timestamp: new Date().toISOString(),
      };
    }

    console.error("[API] Processed Error:", apiError);
    return throwError(() => apiError);
  }

  /**
   * Get user-friendly error message based on HTTP status
   */
  private getDefaultErrorMessage(status: number): string {
    switch (status) {
      case 400:
        return "Invalid request. Please check your input.";
      case 401:
        return "Unauthorized. Please log in again.";
      case 403:
        return "Access forbidden. You do not have permission.";
      case 404:
        return "Resource not found.";
      case 429:
        return "Too many requests. Please try again later.";
      case 500:
        return "Server error. Please try again later.";
      case 503:
        return "Service unavailable. Please try again later.";
      default:
        return "An unexpected error occurred. Please try again.";
    }
  }
}
