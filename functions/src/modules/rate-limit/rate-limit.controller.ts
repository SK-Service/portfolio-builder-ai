import { Body, Controller, Post } from '@nestjs/common';
import {
  CheckRateLimitRequestDto,
  IncrementRateLimitRequestDto,
  RateLimitResponseDto,
} from '../../common/dto/rate-limit.dto';
import { RateLimitService } from './rate-limit.service';

@Controller('rate-limit')
export class RateLimitController {
  constructor(private readonly rateLimitService: RateLimitService) {}

  @Post('check')
  async checkRateLimit(
    @Body() request: CheckRateLimitRequestDto,
  ): Promise<RateLimitResponseDto> {
    return this.rateLimitService.checkRateLimit(request);
  }

  @Post('increment')
  async incrementRateLimit(
    @Body() request: IncrementRateLimitRequestDto,
  ): Promise<RateLimitResponseDto> {
    return this.rateLimitService.incrementRateLimit(request);
  }
}
