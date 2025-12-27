import * as admin from 'firebase-admin';
import * as fs from 'fs';
import * as path from 'path';

let firebaseApp: admin.app.App;

export function initializeFirebase(): admin.app.App {
  // First, check if Firebase Admin was already initialized elsewhere (e.g., main.ts)
  if (admin.apps.length && admin.apps[0]) {
    firebaseApp = admin.apps[0];
    return firebaseApp;
  }

  // Only initialize if not already done
  if (!firebaseApp) {
    const serviceAccountPath = path.join(
      __dirname,
      '../../firebase-service-account.json',
    );

    if (fs.existsSync(serviceAccountPath)) {
      // Read and parse service account JSON (type-safe)
      const serviceAccountJson = fs.readFileSync(serviceAccountPath, 'utf8');
      const serviceAccount = JSON.parse(
        serviceAccountJson,
      ) as admin.ServiceAccount;

      firebaseApp = admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
        projectId: process.env.FIREBASE_PROJECT_ID || 'portfolio-builder-ai',
      });
      console.log('Firebase Admin SDK initialized with service account');
    } else {
      // Production (Firebase handles credentials automatically)
      firebaseApp = admin.initializeApp({
        projectId: process.env.FIREBASE_PROJECT_ID || 'portfolio-builder-ai',
      });
      console.log('Firebase Admin SDK initialized (production)');
    }
  }
  return firebaseApp;
}

export function getFirestore(): admin.firestore.Firestore {
  if (!firebaseApp && !admin.apps.length) {
    initializeFirebase();
  }
  return admin.firestore();
}
