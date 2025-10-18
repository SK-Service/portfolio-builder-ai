import { enableProdMode } from '@angular/core';
import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';
import { environment } from './environments/environment';

if (environment.production) {
  enableProdMode();
}

/**
 * Start MSW if in mock mode
 */
async function prepareMockServiceWorker() {
  if (environment.features.useMockData) {
    const { worker } = await import('./app/mocks/browser');
    
    return worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: {
        url: '/mockServiceWorker.js'  // ← Changed from /assets/mockServiceWorker.js
      }
    });
  }
  
  return Promise.resolve();
}

/**
 * Bootstrap Angular app
 */
prepareMockServiceWorker()
  .then(() => {
    platformBrowserDynamic()
      .bootstrapModule(AppModule)
      .catch(err => console.error(err));
  });