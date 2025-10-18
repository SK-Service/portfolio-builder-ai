// portfolio-builder-ai/frontend/src/app/app.module.ts

import { HttpClientModule, provideHttpClient, withInterceptors } from '@angular/common/http';
import { NgModule } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

// Angular Material Modules
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatToolbarModule } from '@angular/material/toolbar';

// Firebase
import { initializeApp, provideFirebaseApp } from '@angular/fire/app';
import { getFirestore, provideFirestore } from '@angular/fire/firestore';
import { environment } from '../environments/environment';

// App Components
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { HomeComponent } from './components/home/home.component';
import { PortfolioResultsComponent } from './components/portfolio-results/portfolio-results.component';
import { RiskAssessmentComponent } from './components/risk-assessment/risk-assessment.component';

// Services
import { ConfigService } from './services/config.service';
import { LoadingService } from './services/loading.service';
import { LoggerService } from './services/logger.service';
import { PortfolioService } from './services/portfolio.service';
import { RateLimitService } from './services/rate-limit.service';

// Interceptors
import { authInterceptor } from './interceptors/auth.interceptor';
import { errorInterceptor } from './interceptors/error.interceptor';
import { loadingInterceptor } from './interceptors/loading.interceptor';

const firebaseConfig = environment.firebase;

@NgModule({
  declarations: [
    AppComponent,
    HomeComponent,
    RiskAssessmentComponent,
    PortfolioResultsComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    BrowserAnimationsModule,
    ReactiveFormsModule,
    FormsModule,
    HttpClientModule,
    
    // Angular Material
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatToolbarModule,
    MatIconModule,
    MatTableModule,
    MatProgressBarModule
  ],
  providers: [
    provideFirebaseApp(() => initializeApp(firebaseConfig)),
    provideFirestore(() => getFirestore()),
    provideHttpClient(
      withInterceptors([
        authInterceptor,
        loadingInterceptor,
        errorInterceptor
      ])
    ),
    RateLimitService,
    ConfigService,
    PortfolioService,
    LoadingService,
    LoggerService
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }