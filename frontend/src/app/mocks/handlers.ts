import { delay, http, HttpResponse } from 'msw';
import { environment } from '../../environments/environment';
import {
    ApiResponse,
    GeneratePortfolioRequest
} from '../shared/models/api-contracts';
import {
    generateMockPortfolio,
    mockConfig,
    mockRateLimitCheck
} from './mock-data';

const baseUrl = environment.api.baseUrl;

/**
 * MSW Request Handlers
 * These intercept API calls and return mock responses
 */
export const handlers = [
  
  // GET /config - Return application configuration
  http.get(`${baseUrl}/config`, async () => {
    await delay(500); // Simulate network delay
    
    const response: ApiResponse<typeof mockConfig> = {
      success: true,
      data: mockConfig,
      metadata: {
        requestId: generateRequestId(),
        duration: 500
      }
    };
    
    return HttpResponse.json(response);
  }),

  // POST /portfolio/generate - Generate portfolio recommendations
  http.post(`${baseUrl}/portfolio/generate`, async ({ request }) => {
    await delay(2000); // Simulate AI processing time
    
    const body = await request.json() as GeneratePortfolioRequest;
    
    const portfolioData = generateMockPortfolio(
      body.riskTolerance,
      body.investmentHorizonYears,
      body.country,
      body.investmentAmount
    );
    
    const response: ApiResponse<typeof portfolioData> = {
      success: true,
      data: portfolioData,
      metadata: {
        requestId: generateRequestId(),
        duration: 2000
      }
    };
    
    return HttpResponse.json(response);
  }),

  // POST /rate-limit/check - Check rate limit status
  http.post(`${baseUrl}/rate-limit/check`, async ({ request }) => {
    await delay(200);
    
    const response: ApiResponse<typeof mockRateLimitCheck> = {
      success: true,
      data: mockRateLimitCheck,
      metadata: {
        requestId: generateRequestId(),
        duration: 200
      }
    };
    
    return HttpResponse.json(response);
  }),

  // POST /rate-limit/increment - Increment rate limit counter
  http.post(`${baseUrl}/rate-limit/increment`, async ({ request }) => {
    await delay(200);
    
    const response: ApiResponse<any> = {
      success: true,
      data: {
        attemptsUsed: 1,
        attemptsRemaining: 1
      },
      metadata: {
        requestId: generateRequestId(),
        duration: 200
      }
    };
    
    return HttpResponse.json(response);
  })
];

/**
 * Generate mock request ID
 */
function generateRequestId(): string {
  return `mock-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}