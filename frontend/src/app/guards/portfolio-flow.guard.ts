// portfolio-builder-ai/frontend/src/app/guards/portfolio-flow.guard.ts

import { Injectable } from "@angular/core";
import { MatSnackBar } from "@angular/material/snack-bar";
import { CanActivate, Router } from "@angular/router";

@Injectable({
  providedIn: "root",
})
export class PortfolioFlowGuard implements CanActivate {
  private readonly FLOW_FLAG_KEY = "portfolioFlowValid";

  constructor(
    private router: Router,
    private snackBar: MatSnackBar
  ) {}

  canActivate(): boolean {
    const flowValid = sessionStorage.getItem(this.FLOW_FLAG_KEY);

    if (flowValid === "true") {
      // Valid flow - allow access
      // Note: Flag is cleared by portfolio-results component after loading
      return true;
    }

    // Invalid flow - redirect to home
    console.warn(
      "PortfolioFlowGuard: Invalid flow detected, redirecting to home"
    );
    this.showInvalidFlowMessage();
    this.router.navigate(["/"]);
    return false;
  }

  private showInvalidFlowMessage(): void {
    this.snackBar.open(
      "Please start from the beginning to get your portfolio recommendations.",
      "OK",
      {
        duration: 5000,
        panelClass: ["flow-guard-snackbar"],
      }
    );
  }
}
