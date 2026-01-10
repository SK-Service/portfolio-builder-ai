// portfolio-builder-ai/frontend/src/app/app-routing.module.ts

import { NgModule } from "@angular/core";
import { RouterModule, Routes } from "@angular/router";
import { HomeComponent } from "./components/home/home.component";
import { PortfolioResultsComponent } from "./components/portfolio-results/portfolio-results.component";
import { RiskAssessmentComponent } from "./components/risk-assessment/risk-assessment.component";
import { PortfolioFlowGuard } from "./guards/portfolio-flow.guard";
import { RateLimitGuard } from "./guards/rate-limit.guard";

const routes: Routes = [
  { path: "", component: HomeComponent },
  {
    path: "risk-assessment",
    component: RiskAssessmentComponent,
    canActivate: [RateLimitGuard],
  },
  {
    path: "portfolio-results",
    component: PortfolioResultsComponent,
    canActivate: [PortfolioFlowGuard],
  },
  { path: "**", redirectTo: "" }, // Wildcard route for 404s
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes, {
      enableTracing: false, // Set to true for debugging
      scrollPositionRestoration: "top",
    }),
  ],
  exports: [RouterModule],
})
export class AppRoutingModule {}
