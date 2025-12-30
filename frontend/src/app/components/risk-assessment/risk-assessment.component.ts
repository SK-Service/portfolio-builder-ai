// portfolio-builder-ai/frontend/src/app/components/risk-assessment/risk-assessment.component.ts

import { Component, OnInit } from "@angular/core";
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from "@angular/forms";
import { MatSnackBar } from "@angular/material/snack-bar";
import { ActivatedRoute, Router } from "@angular/router";
import { RateLimitService } from "../../services/rate-limit.service";
import {
  Country,
  COUNTRY_CONFIGS,
  CountryConfig,
  Currency,
  DEFAULT_MAX_INVESTMENT,
  RISK_TOLERANCE_OPTIONS,
  RiskAssessment,
} from "../../shared/models";

@Component({
  selector: "app-risk-assessment",
  templateUrl: "./risk-assessment.component.html",
  styleUrls: ["./risk-assessment.component.scss"],
})
export class RiskAssessmentComponent implements OnInit {
  assessmentForm: FormGroup;
  countryConfigs = COUNTRY_CONFIGS;
  riskToleranceOptions = RISK_TOLERANCE_OPTIONS;
  isSubmitting = false;
  selectedCurrency: Currency = "USD";
  selectedCurrencySymbol = "$";

  // Modal state
  showDisclaimerModal = false;

  // Current country config for validation messages
  currentCountryConfig: CountryConfig | null = null;

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar,
    private rateLimitService: RateLimitService
  ) {
    this.assessmentForm = this.fb.group({
      riskTolerance: ["", Validators.required],
      investmentHorizonYears: [
        "",
        [
          Validators.required,
          Validators.min(1),
          Validators.max(30),
          this.wholeNumberValidator(),
        ],
      ],
      country: ["", Validators.required],
      investmentAmount: [
        "",
        [
          Validators.required,
          Validators.min(5000),
          this.multipleOfHundredValidator(),
        ],
      ],
    });
  }

  ngOnInit(): void {
    // Check if disclaimer has been acknowledged this session
    const disclaimerAcknowledged = sessionStorage.getItem(
      "disclaimerAcknowledged"
    );
    if (!disclaimerAcknowledged) {
      this.showDisclaimerModal = true;
    }

    // Check if we are in modify mode
    const mode = this.route.snapshot.queryParamMap.get("mode");
    if (mode === "modify") {
      this.loadExistingAssessment();
    }

    // Subscribe to country changes to update currency and validation
    this.assessmentForm
      .get("country")
      ?.valueChanges.subscribe((country: Country) => {
        if (country) {
          const config = this.countryConfigs.find((c) => c.country === country);
          if (config) {
            this.currentCountryConfig = config;
            this.selectedCurrency = config.currency;
            this.selectedCurrencySymbol = config.symbol;
            // Update validation for investment amount based on country
            this.updateInvestmentAmountValidation(config);
          }
        }
      });
  }

  // Custom validator for whole numbers (no decimals)
  private wholeNumberValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (control.value === null || control.value === "") {
        return null; // Let required validator handle empty values
      }
      const value = Number(control.value);
      if (!Number.isInteger(value)) {
        return { notWholeNumber: true };
      }
      return null;
    };
  }

  // Custom validator for multiples of 100
  private multipleOfHundredValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (control.value === null || control.value === "") {
        return null; // Let required validator handle empty values
      }
      const value = Number(control.value);
      if (value % 100 !== 0) {
        return { notMultipleOfHundred: true };
      }
      return null;
    };
  }

  // Custom validator for max investment amount
  private maxInvestmentValidator(max: number): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (control.value === null || control.value === "") {
        return null;
      }
      const value = Number(control.value);
      if (value > max) {
        return { maxInvestment: { max: max } };
      }
      return null;
    };
  }

  private loadExistingAssessment(): void {
    const stored = sessionStorage.getItem("riskAssessment");
    if (stored) {
      const assessment: RiskAssessment = JSON.parse(stored);

      // Find the country config to set currency info
      const config = this.countryConfigs.find(
        (c) => c.country === assessment.country
      );
      if (config) {
        this.currentCountryConfig = config;
        this.selectedCurrency = config.currency;
        this.selectedCurrencySymbol = config.symbol;
      }

      // Populate the form with existing values
      this.assessmentForm.patchValue({
        riskTolerance: assessment.riskTolerance,
        investmentHorizonYears: assessment.investmentHorizonYears,
        country: assessment.country,
        investmentAmount: assessment.investmentAmount,
      });

      // Update validation after setting country
      if (config) {
        this.updateInvestmentAmountValidation(config);
      }
    }
  }

  private updateInvestmentAmountValidation(config: CountryConfig): void {
    const investmentAmountControl = this.assessmentForm.get("investmentAmount");
    if (investmentAmountControl) {
      const maxAmount = this.getMaxInvestmentForCountry(config);
      investmentAmountControl.setValidators([
        Validators.required,
        Validators.min(config.minInvestmentAmount),
        this.maxInvestmentValidator(maxAmount),
        this.multipleOfHundredValidator(),
      ]);
      investmentAmountControl.updateValueAndValidity();
    }
  }

  // Helper to get max investment amount with fallback
  private getMaxInvestmentForCountry(config: CountryConfig): number {
    // Use config value if available, otherwise use default
    return config.maxInvestmentAmount ?? DEFAULT_MAX_INVESTMENT[config.country];
  }

  acknowledgeDisclaimer(): void {
    sessionStorage.setItem("disclaimerAcknowledged", "true");
    this.showDisclaimerModal = false;
  }

  getMinInvestmentAmount(): number {
    return this.currentCountryConfig?.minInvestmentAmount ?? 5000;
  }

  getMaxInvestmentAmount(): number {
    if (this.currentCountryConfig) {
      return this.getMaxInvestmentForCountry(this.currentCountryConfig);
    }
    return 1000000; // Default fallback
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
            currency: this.selectedCurrency,
          };

          // Store assessment data for next component
          sessionStorage.setItem(
            "riskAssessment",
            JSON.stringify(riskAssessment)
          );

          // Navigate to portfolio results
          this.router.navigate(["/portfolio-results"]);
        },
        error: (error) => {
          console.error("Error incrementing rate limit:", error);
          this.isSubmitting = false;
          this.snackBar.open("An error occurred. Please try again.", "Close", {
            duration: 5000,
          });
        },
      });
    } else {
      this.markFormGroupTouched();
      this.snackBar.open(
        "Please fill in all required fields correctly.",
        "Close",
        {
          duration: 5000,
        }
      );
    }
  }

  private markFormGroupTouched(): void {
    Object.keys(this.assessmentForm.controls).forEach((key) => {
      const control = this.assessmentForm.get(key);
      control?.markAsTouched();
    });
  }

  goBack(): void {
    this.router.navigate(["/"]);
  }

  // Helper methods for template
  hasError(controlName: string, errorType: string): boolean {
    const control = this.assessmentForm.get(controlName);
    return control ? control.hasError(errorType) && control.touched : false;
  }

  getErrorMessage(controlName: string): string {
    const control = this.assessmentForm.get(controlName);
    if (control && control.errors && control.touched) {
      if (control.errors["required"]) {
        return `${this.getFieldLabel(controlName)} is required`;
      }
      if (control.errors["min"]) {
        if (controlName === "investmentAmount") {
          return `Minimum investment amount is ${this.selectedCurrencySymbol}${this.getMinInvestmentAmount().toLocaleString()}`;
        }
        return `${this.getFieldLabel(controlName)} must be at least ${control.errors["min"].min}`;
      }
      if (control.errors["max"]) {
        if (controlName === "investmentHorizonYears") {
          return "Too long a target! Let us plan for something within 30 years.";
        }
        return `Maximum value is ${control.errors["max"].max}`;
      }
      if (control.errors["maxInvestment"]) {
        return `Currently, the app does not support investments above ${this.selectedCurrencySymbol}${control.errors["maxInvestment"].max.toLocaleString()}`;
      }
      if (control.errors["notWholeNumber"]) {
        return "Investment horizon must be a whole number of years";
      }
      if (control.errors["notMultipleOfHundred"]) {
        return "Investment amount must be in multiples of 100";
      }
    }
    return "";
  }

  // Get all error messages for a control (for displaying multiple errors)
  getAllErrorMessages(controlName: string): string[] {
    const control = this.assessmentForm.get(controlName);
    const messages: string[] = [];

    if (control && control.errors && control.touched) {
      if (control.errors["required"]) {
        messages.push(`${this.getFieldLabel(controlName)} is required`);
      }
      if (control.errors["min"]) {
        if (controlName === "investmentAmount") {
          messages.push(
            `Minimum investment amount is ${this.selectedCurrencySymbol}${this.getMinInvestmentAmount().toLocaleString()}`
          );
        } else if (controlName === "investmentHorizonYears") {
          messages.push("Investment horizon must be at least 1 year");
        } else {
          messages.push(`Minimum value is ${control.errors["min"].min}`);
        }
      }
      if (control.errors["max"]) {
        if (controlName === "investmentHorizonYears") {
          messages.push(
            "Too long a target! Let us plan for something within 30 years."
          );
        } else {
          messages.push(`Maximum value is ${control.errors["max"].max}`);
        }
      }
      if (control.errors["maxInvestment"]) {
        messages.push(
          `Currently, the app does not support investments above ${this.selectedCurrencySymbol}${control.errors["maxInvestment"].max.toLocaleString()}`
        );
      }
      if (control.errors["notWholeNumber"]) {
        messages.push("Investment horizon must be a whole number of years");
      }
      if (control.errors["notMultipleOfHundred"]) {
        messages.push("Investment amount must be in multiples of 100");
      }
    }

    return messages;
  }

  private getFieldLabel(controlName: string): string {
    switch (controlName) {
      case "riskTolerance":
        return "Risk tolerance";
      case "investmentHorizonYears":
        return "Investment horizon";
      case "country":
        return "Investment country";
      case "investmentAmount":
        return "Investment amount";
      default:
        return controlName;
    }
  }
}
