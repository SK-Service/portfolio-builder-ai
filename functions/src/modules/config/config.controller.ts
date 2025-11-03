import { Controller, Get } from '@nestjs/common';
import type { AppConfigDto } from '../../common/dto/config.dto';
import { ConfigService } from './config.service';

@Controller('config')
export class ConfigController {
  constructor(private readonly configService: ConfigService) {}

  @Get()
  async getConfig(): Promise<AppConfigDto> {
    return this.configService.getConfig();
  }
}
