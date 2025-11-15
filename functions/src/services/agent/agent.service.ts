import { HttpService } from '@nestjs/axios';
import { HttpException, HttpStatus, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom } from 'rxjs';
import {
  GeneratePortfolioRequestDto,
  PortfolioRecommendationDto,
} from '../../common/dto/portfolio.dto';

@Injectable()
export class AgentService {
  private readonly logger = new Logger(AgentService.name);
  private readonly agentApiUrl: string;
  private readonly agentApiKey: string;

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
  ) {
    const apiUrl = this.configService.get<string>('AGENT_API_URL');
    const apiKey = this.configService.get<string>('AGENT_API_KEY');

    if (!apiUrl || !apiKey) {
      this.logger.error(
        'Agent API configuration missing in environment variables',
      );
      throw new Error(
        'AGENT_API_URL and AGENT_API_KEY must be set in environment',
      );
    }

    this.agentApiUrl = apiUrl;
    this.agentApiKey = apiKey;

    this.logger.log(`Agent API configured at: ${this.agentApiUrl}`);
  }

  async generatePortfolio(
    request: GeneratePortfolioRequestDto,
  ): Promise<PortfolioRecommendationDto> {
    this.logger.log('Calling Agent API to generate portfolio');
    this.logger.debug(`Request: ${JSON.stringify(request)}`);

    try {
      const response = await firstValueFrom(
        this.httpService.post<PortfolioRecommendationDto>(
          this.agentApiUrl,
          request,
          {
            headers: {
              'Content-Type': 'application/json',
              'X-Portfolio-App-Key': this.agentApiKey,
              'X-Requested-With': 'XMLHttpRequest',
            },
            timeout: 60000,
          },
        ),
      );

      this.logger.log('Agent API call successful');
      this.logger.debug(`Response: ${JSON.stringify(response.data)}`);

      return response.data;
    } catch (error: unknown) {
      this.logger.error(
        'Agent API call failed',
        error instanceof Error ? error.message : 'Unknown error',
      );

      if (this.isAxiosError(error)) {
        if (error.response?.status === 403) {
          throw new HttpException(
            'Agent API authentication failed',
            HttpStatus.FORBIDDEN,
          );
        }

        if (error.response?.status === 400) {
          const errorMessage = error.response.data?.error || 'Invalid request';
          throw new HttpException(
            `Agent API validation error: ${errorMessage}`,
            HttpStatus.BAD_REQUEST,
          );
        }

        if (error.code === 'ECONNREFUSED') {
          throw new HttpException(
            'Agent API is not running. Please start the Firebase emulator.',
            HttpStatus.SERVICE_UNAVAILABLE,
          );
        }
      }

      throw new HttpException(
        `Failed to generate portfolio: ${error instanceof Error ? error.message : 'Unknown error'}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  private isAxiosError(error: unknown): error is {
    response?: { status: number; data?: { error?: string } };
    code?: string;
    message: string;
  } {
    return (
      typeof error === 'object' &&
      error !== null &&
      ('response' in error || 'code' in error)
    );
  }
}
