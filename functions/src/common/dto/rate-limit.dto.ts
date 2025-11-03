import { IsString } from 'class-validator';

export class CheckRateLimitRequestDto {
  @IsString()
  fingerprint: string;
}

export class RateLimitResponseDto {
  allowed: boolean;
  attemptsRemaining: number;
  attemptsUsed: number;
  resetAt: string;
}

export class IncrementRateLimitRequestDto {
  @IsString()
  fingerprint: string;
}
