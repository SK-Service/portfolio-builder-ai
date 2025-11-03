import { MiddlewareConsumer, Module, NestModule } from '@nestjs/common';
import { ConfigModule as NestConfigModule } from '@nestjs/config';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { SecurityMiddleware } from './common/middleware/security.middleware';
import { ConfigModule } from './modules/config/config.module';
import { PortfolioModule } from './modules/portfolio/portfolio.module';
import { RateLimitModule } from './modules/rate-limit/rate-limit.module';
import { FirestoreService } from './services/firestore.service';
import { MockAgentService } from './services/mocks/mock-agent.service';

@Module({
  imports: [
    NestConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
    ConfigModule,
    PortfolioModule,
    RateLimitModule,
  ],
  controllers: [AppController],
  providers: [AppService, MockAgentService, FirestoreService],
  exports: [FirestoreService],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer.apply(SecurityMiddleware).forRoutes('*');
  }
}
