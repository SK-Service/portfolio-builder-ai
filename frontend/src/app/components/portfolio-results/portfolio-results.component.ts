// portfolio-builder-ai/frontend/src/app/components/portfolio-results/portfolio-results.component.ts

import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from "@angular/core";
import { Router } from "@angular/router";
import {
  Chart,
  ChartConfiguration,
  TooltipItem,
  registerables,
} from "chart.js";
import { PortfolioService } from "../../services/portfolio.service";
import { PortfolioRecommendation, RiskAssessment } from "../../shared/models";

interface CachedPortfolio {
  cacheKey: string;
  portfolio: PortfolioRecommendation;
  cachedAt: string;
}

@Component({
  selector: "app-portfolio-results",
  templateUrl: "./portfolio-results.component.html",
  styleUrls: ["./portfolio-results.component.scss"],
})
export class PortfolioResultsComponent
  implements OnInit, AfterViewInit, OnDestroy
{
  @ViewChild("pieChartCanvas", { static: false })
  pieChartCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild("lineChartCanvas", { static: false })
  lineChartCanvas!: ElementRef<HTMLCanvasElement>;

  riskAssessment: RiskAssessment | null = null;
  portfolioRecommendation: PortfolioRecommendation | null = null;
  isLoading = true;

  private pieChart: Chart | null = null;
  private lineChart: Chart | null = null;

  private readonly PORTFOLIO_CACHE_KEY = "portfolio_cache";
  private readonly FLOW_FLAG_KEY = "portfolioFlowValid";

  displayedColumns: string[] = [
    "symbol",
    "companyName",
    "sector",
    "allocation",
    "expectedReturn",
  ];

  constructor(
    private router: Router,
    private portfolioService: PortfolioService
  ) {
    Chart.register(...registerables);
  }

  ngOnInit(): void {
    this.loadRiskAssessment();
    if (this.riskAssessment) {
      this.loadOrGeneratePortfolio();
    }
  }

  ngAfterViewInit(): void {
    // Charts created after data loads
  }

  ngOnDestroy(): void {
    if (this.pieChart) {
      this.pieChart.destroy();
    }
    if (this.lineChart) {
      this.lineChart.destroy();
    }
  }

  private loadRiskAssessment(): void {
    const stored = sessionStorage.getItem("riskAssessment");
    if (stored) {
      this.riskAssessment = JSON.parse(stored);
    } else {
      this.router.navigate(["/risk-assessment"]);
      return;
    }
  }

  /**
   * Generate a cache key from risk assessment inputs
   * This ensures cache is only used when inputs are identical
   */
  private generateCacheKey(assessment: RiskAssessment): string {
    return `${assessment.riskTolerance}_${assessment.investmentHorizonYears}_${assessment.country}_${assessment.investmentAmount}_${assessment.currency}`;
  }

  /**
   * Try to load portfolio from cache, otherwise generate new one
   */
  private loadOrGeneratePortfolio(): void {
    if (!this.riskAssessment) return;

    const currentCacheKey = this.generateCacheKey(this.riskAssessment);
    const cachedData = this.getCachedPortfolio();

    // Check if we have a valid cached portfolio for the same inputs
    if (cachedData && cachedData.cacheKey === currentCacheKey) {
      console.log("Portfolio loaded from cache");
      this.portfolioRecommendation = cachedData.portfolio;
      this.isLoading = false;
      // Clear flow flag since we've successfully loaded
      this.clearFlowFlag();
      setTimeout(() => this.setupCharts(), 100);
      return;
    }

    // No valid cache, generate new portfolio
    this.generatePortfolioRecommendation();
  }

  /**
   * Get cached portfolio from sessionStorage
   */
  private getCachedPortfolio(): CachedPortfolio | null {
    try {
      const stored = sessionStorage.getItem(this.PORTFOLIO_CACHE_KEY);
      if (stored) {
        return JSON.parse(stored) as CachedPortfolio;
      }
    } catch (error) {
      console.warn("Error reading portfolio cache:", error);
    }
    return null;
  }

  /**
   * Save portfolio to sessionStorage cache
   */
  private cachePortfolio(portfolio: PortfolioRecommendation): void {
    if (!this.riskAssessment) return;

    try {
      const cacheData: CachedPortfolio = {
        cacheKey: this.generateCacheKey(this.riskAssessment),
        portfolio: portfolio,
        cachedAt: new Date().toISOString(),
      };
      sessionStorage.setItem(
        this.PORTFOLIO_CACHE_KEY,
        JSON.stringify(cacheData)
      );
      console.log("Portfolio cached successfully");
    } catch (error) {
      console.warn("Error caching portfolio:", error);
    }
  }

  /**
   * Clear the portfolio cache
   */
  private clearPortfolioCache(): void {
    sessionStorage.removeItem(this.PORTFOLIO_CACHE_KEY);
  }

  /**
   * Clear the flow validation flag
   * This prevents direct access via bookmark after initial load
   */
  private clearFlowFlag(): void {
    sessionStorage.removeItem(this.FLOW_FLAG_KEY);
  }

  private generatePortfolioRecommendation(): void {
    if (!this.riskAssessment) return;

    this.isLoading = true;

    this.portfolioService
      .generatePortfolioRecommendation(this.riskAssessment)
      .subscribe({
        next: (recommendation) => {
          this.portfolioRecommendation = recommendation;
          // Cache the successful result
          this.cachePortfolio(recommendation);
          // Clear flow flag after successful generation
          this.clearFlowFlag();
          setTimeout(() => this.setupCharts(), 100);
          this.isLoading = false;
        },
        error: (error) => {
          console.error("Error generating portfolio:", error);
          this.isLoading = false;
          // Clear flow flag even on error to prevent retry via refresh
          this.clearFlowFlag();
        },
      });
  }

  private setupCharts(): void {
    if (
      !this.portfolioRecommendation ||
      !this.pieChartCanvas ||
      !this.lineChartCanvas
    )
      return;

    this.createPieChart();
    this.createLineChart();
  }

  private createPieChart(): void {
    if (!this.portfolioRecommendation || !this.pieChartCanvas) return;

    const ctx = this.pieChartCanvas.nativeElement.getContext("2d");
    if (!ctx) return;

    if (this.pieChart) {
      this.pieChart.destroy();
    }

    const config: ChartConfiguration<"pie"> = {
      type: "pie",
      data: {
        labels: this.portfolioRecommendation.recommendations.map(
          (r) => r.symbol
        ),
        datasets: [
          {
            data: this.portfolioRecommendation.recommendations.map(
              (r) => r.allocation
            ),
            backgroundColor: [
              "#1976d2",
              "#388e3c",
              "#f57c00",
              "#d32f2f",
              "#7b1fa2",
              "#303f9f",
              "#455a64",
              "#512da8",
            ],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
          },
          tooltip: {
            callbacks: {
              label: (context: TooltipItem<"pie">) => {
                const label = context.label || "";
                const value = context.parsed || 0;
                return `${label}: ${value.toFixed(1)}%`;
              },
            },
          },
        },
      },
    };

    this.pieChart = new Chart(ctx, config) as Chart;
  }

  private createLineChart(): void {
    if (
      !this.portfolioRecommendation ||
      !this.lineChartCanvas ||
      !this.riskAssessment
    )
      return;

    const ctx = this.lineChartCanvas.nativeElement.getContext("2d");
    if (!ctx) return;

    if (this.lineChart) {
      this.lineChart.destroy();
    }

    const years = this.portfolioRecommendation.projectedGrowth.map(
      (p) => p.year
    );
    const values = this.portfolioRecommendation.projectedGrowth.map(
      (p) => p.projectedValue
    );

    const config: ChartConfiguration<"line"> = {
      type: "line",
      data: {
        labels: years.map((y) => y.toString()),
        datasets: [
          {
            data: values,
            label: `Projected Value (${this.riskAssessment.currency})`,
            borderColor: "#1976d2",
            backgroundColor: "rgba(25, 118, 210, 0.1)",
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: {
              display: true,
              text: "Years",
            },
          },
          y: {
            title: {
              display: true,
              text: "Portfolio Value",
            },
          },
        },
        plugins: {
          legend: {
            display: true,
          },
        },
      },
    };

    this.lineChart = new Chart(ctx, config) as Chart;
  }

  startNewAssessment(): void {
    // Clear both risk assessment and portfolio cache
    sessionStorage.removeItem("riskAssessment");
    this.clearPortfolioCache();
    this.router.navigate(["/"]);
  }

  modifyAssessment(): void {
    // Clear portfolio cache so new inputs will generate fresh portfolio
    this.clearPortfolioCache();
    // Navigate to risk assessment with modify mode query parameter
    // This preserves the existing assessment data and pre-populates the form
    this.router.navigate(["/risk-assessment"], {
      queryParams: { mode: "modify" },
    });
  }

  formatCurrency(amount: number): string {
    if (!this.riskAssessment) return amount.toString();

    const symbol = this.getCurrencySymbol();
    return `${symbol}${amount.toLocaleString()}`;
  }

  private getCurrencySymbol(): string {
    switch (this.riskAssessment?.currency) {
      case "USD":
        return "$";
      case "EUR":
        return "€";
      case "CAD":
        return "C$";
      case "INR":
        return "₹";
      default:
        return "$";
    }
  }

  getRiskDescription(): string {
    switch (this.riskAssessment?.riskTolerance) {
      case "Low":
        return "Conservative approach with lower volatility";
      case "Medium":
        return "Balanced approach with moderate growth potential";
      case "High":
        return "Aggressive approach focused on maximum growth";
      default:
        return "";
    }
  }
}
