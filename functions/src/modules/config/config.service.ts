import { Injectable } from '@nestjs/common';
import { AppConfigDto } from '../../common/dto/config.dto';
import { FirestoreService } from '../../services/firestore.service';
import { mockConfig } from '../../services/mocks/mock-data';

@Injectable()
export class ConfigService {
  constructor(private readonly firestoreService: FirestoreService) {}

  async getConfig(): Promise<AppConfigDto> {
    try {
      const config = await this.firestoreService.getAppConfig();

      if (!config) {
        console.warn('No config in Firestore, using mock data');
        return mockConfig;
      }

      console.log('Config loaded from Firestore');
      return config;
    } catch (error) {
      console.error(
        'Error loading config from Firestore, falling back to mock:',
        error,
      );
      return mockConfig;
    }
  }
}
