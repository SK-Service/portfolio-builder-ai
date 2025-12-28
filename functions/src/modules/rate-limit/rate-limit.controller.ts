import { Body, Controller, Post } from '@nestjs/common';
import {
  CheckRateLimitRequestDto,
  IncrementRateLimitRequestDto,
  RateLimitResponseDto,
} from '../../common/dto/rate-limit.dto';
import { RateLimitService } from './rate-limit.service';

interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

@Controller('rate-limit')
export class RateLimitController {
  constructor(private readonly rateLimitService: RateLimitService) {}

  @Post('check')
  async checkRateLimit(
    @Body() request: CheckRateLimitRequestDto,
  ): Promise<ApiResponse<RateLimitResponseDto>> {
    const result = await this.rateLimitService.checkRateLimit(request);
    return {
      success: true,
      data: result,
      message: 'Rate limit checked successfully',
    };
  }

  @Post('increment')
  async incrementRateLimit(
    @Body() request: IncrementRateLimitRequestDto,
  ): Promise<ApiResponse<RateLimitResponseDto>> {
    const result = await this.rateLimitService.incrementRateLimit(request);
    return {
      success: true,
      data: result,
      message: 'Rate limit incremented successfully',
    };
  }
}
