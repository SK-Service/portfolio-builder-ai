import { Injectable } from '@angular/core';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class LoggerService {

  debug(message: string, ...args: any[]): void {
    if (environment.features.enableLogging) {
      console.log(`[DEBUG] ${message}`, ...args);
    }
  }

  info(message: string, ...args: any[]): void {
    if (environment.features.enableLogging) {
      console.info(`[INFO] ${message}`, ...args);
    }
  }

  warn(message: string, ...args: any[]): void {
    // Always log warnings
    console.warn(`[WARN] ${message}`, ...args);
  }

  error(message: string, ...args: any[]): void {
    // Always log errors
    console.error(`[ERROR] ${message}`, ...args);
  }

  log(message: string, ...args: any[]): void {
    if (environment.features.enableLogging) {
      console.log(message, ...args);
    }
  }
}