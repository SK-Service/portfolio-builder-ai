import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class LoadingService {
  private loadingSubject = new BehaviorSubject<boolean>(false);
  private activeRequests = 0;

  public loading$: Observable<boolean> = this.loadingSubject.asObservable();

  /**
   * Show loading indicator
   */
  show(): void {
    this.activeRequests++;
    if (this.activeRequests > 0) {
      this.loadingSubject.next(true);
    }
  }

  /**
   * Hide loading indicator
   */
  hide(): void {
    this.activeRequests--;
    if (this.activeRequests <= 0) {
      this.activeRequests = 0;
      this.loadingSubject.next(false);
    }
  }

  /**
   * Get current loading state
   */
  isLoading(): boolean {
    return this.loadingSubject.value;
  }

  /**
   * Reset loading state (useful for error scenarios)
   */
  reset(): void {
    this.activeRequests = 0;
    this.loadingSubject.next(false);
  }
}