// portfolio-builder-ai/frontend/src/app/components/risk-assessment/risk-assessment.component.ts

import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { RateLimitService } from '../../services/rate-limit.service';
import { Country, COUNTRY_CONFIGS, Currency, RISK_TOLERANCE_OPTIONS, RiskAssessment } from '../../shared/models';

@Component({
  selector: 'app-risk-assessment',
  templateUrl: './risk-assessment.component.html',
  styleUrls: ['./risk-assessment.component.scss']
})
export class RiskAssessmentComponent implements OnInit {
  assessmentForm: FormGroup;
  countryConfigs = COUNTRY_CONFIGS;
  riskToleranceOptions = RISK_TOLERANCE_OPTIONS;
  isSubmitting = false;
  selectedCurrency: Currency = 'USD';
  selectedCurrencySymbol = '$';

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private snackBar: MatSnackBar,
    private rateLimitService: RateLimitService
  ) {
    this.assessmentForm = this.fb.group({
      riskTolerance: ['', Validators.required],
      investmentHorizonYears: ['', [Validators.required, Validators.min(1), Validators.max(50)]],
      country: ['', Validators.required],
      investmentAmount: ['', [Validators.required, Validators.min(100)]]
    });
  }

  ngOnInit(): void {
    // Subscribe to country changes to update currency
    this.assessmentForm.get('country')?.valueChanges.subscribe((country: Country) => {
      if (country) {
        const config = this.countryConfigs.find(c => c.country === country);
        if (config) {
          this.selectedCurrency = config.currency;
          this.selectedCurrencySymbol = config.symbol;
          // Update validation for investment amount based on currency
          this.updateInvestmentAmountValidation(country);
        }
      }
    });
  }

  private updateInvestmentAmountValidation(country: Country): void {
    const investmentAmountControl = this.assessmentForm.get('investmentAmount');
    if (investmentAmountControl) {
      let minAmount = 100;
      
      switch (country) {
        case 'USA':
        case 'Canada':
          minAmount = 100;
          break;
        case 'EU':
          minAmount = 100;
          break;
        case 'India':
          minAmount = 5000;
          break;
      }
      
      investmentAmountControl.setValidators([
        Validators.required,
        Validators.min(minAmount)
      ]);
      investmentAmountControl.updateValueAndValidity();
    }
  }

  getMinInvestmentAmount(): number {
    const country = this.assessmentForm.get('country')?.value;
    switch (country) {
      case 'USA':
      case 'Canada':
      case 'EU':
        return 100;
      case 'India':
        return 5000;
      default:
        return 100;
    }
  }

  onSubmit(): void {
    if (this.assessmentForm.valid) {
      this.isSubmitting = true;
      
      // Increment rate limit attempt
      this.rateLimitService.incrementAttempt().subscribe({
        next: () => {
          const formValue = this.assessmentForm.value;
          const riskAssessment: RiskAssessment = {
            riskTolerance: formValue.riskTolerance,
            investmentHorizonYears: Number(formValue.investmentHorizonYears),
            country: formValue.country,
            investmentAmount: Number(formValue.investmentAmount),
            currency: this.selectedCurrency
          };

          // Store assessment data for next component
          sessionStorage.setItem('riskAssessment', JSON.stringify(riskAssessment));
          
          // Navigate to portfolio results
          this.router.navigate(['/portfolio-results']);
        },
        error: (error) => {
          console.error('Error incrementing rate limit:', error);
          this.isSubmitting = false;
          this.snackBar.open('An error occurred. Please try again.', 'Close', {
            duration: 5000
          });
        }
      });
    } else {
      this.markFormGroupTouched();
      this.snackBar.open('Please fill in all required fields correctly.', 'Close', {
        duration: 5000
      });
    }
  }

  private markFormGroupTouched(): void {
    Object.keys(this.assessmentForm.controls).forEach(key => {
      const control = this.assessmentForm.get(key);
      control?.markAsTouched();
    });
  }

  goBack(): void {
    this.router.navigate(['/']);
  }

  // Helper methods for template
  hasError(controlName: string, errorType: string): boolean {
    const control = this.assessmentForm.get(controlName);
    return control ? control.hasError(errorType) && control.touched : false;
  }

  getErrorMessage(controlName: string): string {
    const control = this.assessmentForm.get(controlName);
    if (control && control.errors && control.touched) {
      if (control.errors['required']) {
        return `${this.getFieldLabel(controlName)} is required`;
      }
      if (control.errors['min']) {
        if (controlName === 'investmentAmount') {
          return `Minimum investment amount is ${this.selectedCurrencySymbol}${this.getMinInvestmentAmount()}`;
        }
        return `Minimum value is ${control.errors['min'].min}`;
      }
      if (control.errors['max']) {
        return `Maximum value is ${control.errors['max'].max}`;
      }
    }
    return '';
  }

  private getFieldLabel(controlName: string): string {
    switch (controlName) {
      case 'riskTolerance': return 'Risk tolerance';
      case 'investmentHorizonYears': return 'Investment horizon';
      case 'country': return 'Investment country';
      case 'investmentAmount': return 'Investment amount';
      default: return controlName;
    }
  }
}