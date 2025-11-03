import { Module } from '@nestjs/common';
import { FirestoreService } from '../../services/firestore.service';
import { ConfigController } from './config.controller';
import { ConfigService } from './config.service';

@Module({
  controllers: [ConfigController],
  providers: [ConfigService, FirestoreService],
  exports: [ConfigService],
})
export class ConfigModule {}
