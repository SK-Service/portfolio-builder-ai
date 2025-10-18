import {
    AppConfigDto,
    Country,
    PortfolioRecommendationDto,
    RateLimitCheckDto,
    RiskTolerance
} from '../shared/models/api-contracts';

/**
 * Mock configuration data
 */
export const mockConfig: AppConfigDto = {
  maxFreeAttempts: 2,
  rateLimitWindowHours: 24,
  supportedCountries: [
    { country: 'USA', currency: 'USD', symbol: '$', minInvestmentAmount: 100 },
    { country: 'EU', currency: 'EUR', symbol: '€', minInvestmentAmount: 100 },
    { country: 'Canada', currency: 'CAD', symbol: 'C$', minInvestmentAmount: 100 },
    { country: 'India', currency: 'INR', symbol: '₹', minInvestmentAmount: 5000 }
  ],
  features: {
    maintenanceMode: false,
    newUserSignupEnabled: true
  }
};

/**
 * Mock stock database by country
 */
const mockStocksByCountry = {
  'USA': [
    { symbol: 'AAPL', companyName: 'Apple Inc.', sector: 'Technology', baseReturn: 12.5 },
    { symbol: 'MSFT', companyName: 'Microsoft Corporation', sector: 'Technology', baseReturn: 11.8 },
    { symbol: 'GOOGL', companyName: 'Alphabet Inc.', sector: 'Technology', baseReturn: 13.2 },
    { symbol: 'AMZN', companyName: 'Amazon.com Inc.', sector: 'Consumer Discretionary', baseReturn: 14.1 },
    { symbol: 'TSLA', companyName: 'Tesla Inc.', sector: 'Automotive', baseReturn: 18.5 },
    { symbol: 'JPM', companyName: 'JPMorgan Chase & Co.', sector: 'Financial Services', baseReturn: 9.2 },
    { symbol: 'JNJ', companyName: 'Johnson & Johnson', sector: 'Healthcare', baseReturn: 7.8 },
    { symbol: 'V', companyName: 'Visa Inc.', sector: 'Financial Services', baseReturn: 10.4 }
  ],
  'EU': [
    { symbol: 'ASML', companyName: 'ASML Holding N.V.', sector: 'Technology', baseReturn: 15.2 },
    { symbol: 'SAP', companyName: 'SAP SE', sector: 'Technology', baseReturn: 9.8 },
    { symbol: 'NESN', companyName: 'Nestlé S.A.', sector: 'Consumer Goods', baseReturn: 6.5 },
    { symbol: 'RYDAF', companyName: 'Royal Dutch Shell', sector: 'Energy', baseReturn: 8.2 },
    { symbol: 'NOVN', companyName: 'Novartis AG', sector: 'Healthcare', baseReturn: 7.1 },
    { symbol: 'LVMUY', companyName: 'LVMH', sector: 'Consumer Discretionary', baseReturn: 12.8 }
  ],
  'Canada': [
    { symbol: 'SHOP', companyName: 'Shopify Inc.', sector: 'Technology', baseReturn: 16.3 },
    { symbol: 'RY', companyName: 'Royal Bank of Canada', sector: 'Financial Services', baseReturn: 8.7 },
    { symbol: 'CNR', companyName: 'Canadian National Railway', sector: 'Transportation', baseReturn: 9.5 },
    { symbol: 'BNS', companyName: 'Bank of Nova Scotia', sector: 'Financial Services', baseReturn: 8.2 },
    { symbol: 'TRI', companyName: 'Thomson Reuters Corp.', sector: 'Information Services', baseReturn: 10.1 }
  ],
  'India': [
    { symbol: 'TCS', companyName: 'Tata Consultancy Services', sector: 'Technology', baseReturn: 14.8 },
    { symbol: 'RELIANCE', companyName: 'Reliance Industries Ltd.', sector: 'Energy', baseReturn: 13.2 },
    { symbol: 'INFY', companyName: 'Infosys Limited', sector: 'Technology', baseReturn: 13.9 },
    { symbol: 'HDFC', companyName: 'HDFC Bank Limited', sector: 'Financial Services', baseReturn: 11.5 },
    { symbol: 'BHARTIARTL', companyName: 'Bharti Airtel Limited', sector: 'Telecommunications', baseReturn: 10.8 },
    { symbol: 'ITC', companyName: 'ITC Limited', sector: 'Consumer Goods', baseReturn: 8.9 }
  ]
};

/**
 * Generate mock portfolio based on risk assessment
 */
export function generateMockPortfolio(
  riskTolerance: RiskTolerance,
  investmentHorizonYears: number,
  country: Country,
  investmentAmount: number
): PortfolioRecommendationDto {
  const availableStocks = mockStocksByCountry[country] || mockStocksByCountry['USA'];
  
  // Select number of stocks based on risk
  const numberOfStocks = riskTolerance === 'Low' ? 6 : riskTolerance === 'High' ? 4 : 5;
  
  // Filter stocks based on risk tolerance
  let filteredStocks = [...availableStocks];
  if (riskTolerance === 'Low') {
    filteredStocks = filteredStocks.filter(s => 
      ['Healthcare', 'Consumer Goods', 'Financial Services'].includes(s.sector) || s.baseReturn < 12
    );
  } else if (riskTolerance === 'High') {
    filteredStocks = filteredStocks.filter(s => 
      ['Technology', 'Consumer Discretionary', 'Automotive'].includes(s.sector) || s.baseReturn > 10
    );
  }
  
  if (filteredStocks.length < numberOfStocks) {
    filteredStocks = availableStocks;
  }
  
  // Shuffle and select
  const shuffled = filteredStocks.sort(() => 0.5 - Math.random());
  const selectedStocks = shuffled.slice(0, numberOfStocks);
  
  // Generate allocations
  const allocations = generateAllocations(numberOfStocks, riskTolerance);
  
  // Generate recommendations
  const recommendations = selectedStocks.map((stock, index) => ({
    symbol: stock.symbol,
    companyName: stock.companyName,
    allocation: allocations[index],
    expectedReturn: adjustReturnForRisk(stock.baseReturn, riskTolerance),
    sector: stock.sector,
    country: country
  }));
  
  // Calculate total return
  const totalExpectedReturn = recommendations.reduce((total, stock) => 
    total + (stock.expectedReturn * stock.allocation / 100), 0
  );
  
  // Generate projected growth
  const projectedGrowth = [];
  for (let year = 0; year <= investmentHorizonYears; year++) {
    const projectedValue = investmentAmount * Math.pow(1 + (totalExpectedReturn / 100), year);
    projectedGrowth.push({
      year,
      projectedValue: Math.round(projectedValue)
    });
  }
  
  const riskScore = riskTolerance === 'Low' ? 3.2 : riskTolerance === 'High' ? 8.1 : 5.8;
  
  return {
    recommendations,
    totalExpectedReturn: Math.round(totalExpectedReturn * 10) / 10,
    riskScore,
    projectedGrowth,
    generatedAt: new Date().toISOString()
  };
}

function generateAllocations(numberOfStocks: number, riskTolerance: RiskTolerance): number[] {
  let allocations: number[] = [];
  
  if (riskTolerance === 'Low') {
    const baseAllocation = 100 / numberOfStocks;
    allocations = Array(numberOfStocks).fill(baseAllocation);
    allocations = allocations.map(a => a + (Math.random() - 0.5) * 4);
  } else if (riskTolerance === 'High') {
    allocations.push(35 + Math.random() * 10);
    allocations.push(25 + Math.random() * 8);
    const remaining = 100 - allocations.reduce((sum, curr) => sum + curr, 0);
    const remainingStocks = numberOfStocks - allocations.length;
    for (let i = 0; i < remainingStocks; i++) {
      allocations.push((remaining / remainingStocks) + (Math.random() - 0.5) * 3);
    }
  } else {
    const baseAllocation = 100 / numberOfStocks;
    allocations = Array(numberOfStocks).fill(baseAllocation);
    allocations = allocations.map(a => a + (Math.random() - 0.5) * 6);
  }
  
  // Normalize
  const sum = allocations.reduce((total, curr) => total + curr, 0);
  allocations = allocations.map(a => (a / sum) * 100);
  
  return allocations.map(a => Math.round(a * 10) / 10);
}

function adjustReturnForRisk(baseReturn: number, riskTolerance: RiskTolerance): number {
  const adjustment = riskTolerance === 'Low' ? 0.8 : riskTolerance === 'High' ? 1.15 : 0.95;
  return Math.round((baseReturn * adjustment) * 10) / 10;
}

/**
 * Mock rate limit check - always allows in mock mode
 */
export const mockRateLimitCheck: RateLimitCheckDto = {
  allowed: true,
  attemptsRemaining: 2,
  attemptsUsed: 0,
  resetAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // 24 hours from now
};