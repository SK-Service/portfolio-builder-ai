export class CountryConfigDto {
  country: string;
  currency: string;
  symbol: string;
  minInvestmentAmount: number;
}

export class AppConfigDto {
  maxFreeAttempts: number;
  rateLimitWindowHours: number;
  supportedCountries: CountryConfigDto[];
  features: {
    maintenanceMode: boolean;
    newUserSignupEnabled: boolean;
  };
}
