import * as admin from 'firebase-admin';

let firebaseApp: admin.app.App;

export function initializeFirebase(): admin.app.App {
  if (!firebaseApp) {
    firebaseApp = admin.initializeApp({
      projectId: process.env.FIREBASE_PROJECT_ID || 'portfolio-builder-ai',
    });
    console.log('Firebase Admin SDK initialized');
  }
  return firebaseApp;
}

export function getFirestore(): admin.firestore.Firestore {
  if (!firebaseApp) {
    initializeFirebase();
  }
  return admin.firestore();
}
