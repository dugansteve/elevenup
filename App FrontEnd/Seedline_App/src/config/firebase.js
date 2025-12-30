/**
 * Firebase Configuration
 *
 * Supports multiple brands (Seedline and ElevenUp) with separate Firebase projects.
 * Brand is determined by VITE_BRAND environment variable at build time.
 *
 * SETUP INSTRUCTIONS:
 * 1. Go to https://console.firebase.google.com/
 * 2. Create/access your Firebase project
 * 3. Enable Firebase Storage in the project
 * 4. Go to Project Settings > General > Your apps > Add app > Web
 * 5. Copy the firebaseConfig object and paste it below
 * 6. Set up Storage security rules (see below)
 *
 * STORAGE RULES (paste in Firebase Console > Storage > Rules):
 * ```
 * rules_version = '2';
 * service firebase.storage {
 *   match /b/{bucket}/o {
 *     match /player-photos/{userId}/{claimId}/{fileName} {
 *       allow read: if true;  // Public read for player photos
 *       allow write: if request.auth != null;  // Authenticated users can upload
 *     }
 *   }
 * }
 * ```
 */

import { initializeApp } from 'firebase/app';
import { getStorage, ref, uploadBytes, getDownloadURL, deleteObject } from 'firebase/storage';
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  onAuthStateChanged,
  updateProfile
} from 'firebase/auth';
import { isElevenUpBrand } from './brand';

// Firebase configurations for each brand
const FIREBASE_CONFIGS = {
  seedline: {
    apiKey: "AIzaSyCi1rtxyRhkhYCH7fAueHk4CSDsIs5qCsc",
    authDomain: "seedline-app.firebaseapp.com",
    projectId: "seedline-app",
    storageBucket: "seedline-app.firebasestorage.app",
    messagingSenderId: "670097834344",
    appId: "1:670097834344:web:0f6251f79ef01d8c66d6dd",
    measurementId: "G-06M2JLT4RD"
  },
  elevenup: {
    apiKey: "AIzaSyDTTYMs7KzxO5x50hRe8EL1hTCU8s4_X2Y",
    authDomain: "elevenupsoccer.firebaseapp.com",
    projectId: "elevenupsoccer",
    storageBucket: "elevenupsoccer.firebasestorage.app",
    messagingSenderId: "755090353968",
    appId: "1:755090353968:web:f2a8b780abf4737a0362f5",
    measurementId: "G-HNZC3XLFGN"
  }
};

// Select config based on brand
const firebaseConfig = isElevenUpBrand ? FIREBASE_CONFIGS.elevenup : FIREBASE_CONFIGS.seedline;

// Initialize Firebase (only if config is set)
let app = null;
let storage = null;
let auth = null;

const isConfigured = firebaseConfig.apiKey !== "YOUR_API_KEY";

if (isConfigured) {
  try {
    app = initializeApp(firebaseConfig);
    storage = getStorage(app);
    auth = getAuth(app);
    console.log('Firebase initialized successfully');
  } catch (error) {
    console.error('Firebase initialization error:', error);
  }
}

/**
 * Check if Firebase is properly configured
 * NOTE: Disabled for now - Firebase Storage has CORS issues from localhost
 * Photos will be stored as data URLs in the database instead
 */
export function isFirebaseConfigured() {
  // Disabled - use local storage instead until Firebase CORS is configured
  return false;
  // return isConfigured && storage !== null;
}

/**
 * Upload a player photo to Firebase Storage
 * @param {number} userId - The user's ID
 * @param {number} claimId - The claim ID
 * @param {File} file - The image file to upload
 * @returns {Promise<string>} The download URL of the uploaded image
 */
export async function uploadPlayerPhoto(userId, claimId, file) {
  if (!isFirebaseConfigured()) {
    throw new Error('Firebase is not configured. Please set up your Firebase project.');
  }

  // Validate file type
  const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
  if (!validTypes.includes(file.type)) {
    throw new Error('Invalid file type. Please upload a JPEG, PNG, GIF, or WebP image.');
  }

  // Validate file size (max 2MB)
  const maxSize = 2 * 1024 * 1024; // 2MB
  if (file.size > maxSize) {
    throw new Error('File too large. Maximum size is 2MB.');
  }

  // Create storage reference
  // Handle both File objects (with .name) and Blob objects (without .name)
  let fileExtension = 'jpg'; // default
  if (file.name) {
    fileExtension = file.name.split('.').pop().toLowerCase();
  } else if (file.type) {
    // Extract extension from MIME type (e.g., 'image/jpeg' -> 'jpeg')
    const mimeExt = file.type.split('/')[1];
    fileExtension = mimeExt === 'jpeg' ? 'jpg' : mimeExt;
  }
  const fileName = `photo.${fileExtension}`;
  const storageRef = ref(storage, `player-photos/${userId}/${claimId}/${fileName}`);

  // Upload file
  const snapshot = await uploadBytes(storageRef, file);
  console.log('Uploaded photo:', snapshot.metadata.fullPath);

  // Get download URL
  const downloadURL = await getDownloadURL(storageRef);
  return downloadURL;
}

/**
 * Upload an avatar configuration as JSON
 * @param {number} userId - The user's ID
 * @param {number} claimId - The claim ID
 * @param {Object} avatarConfig - The avatar configuration object
 * @returns {Promise<string>} The download URL of the uploaded config
 */
export async function uploadAvatarConfig(userId, claimId, avatarConfig) {
  if (!isFirebaseConfigured()) {
    // For avatar configs, we can store in the database instead
    // Just return null and let the backend handle it
    return null;
  }

  const configBlob = new Blob([JSON.stringify(avatarConfig)], { type: 'application/json' });
  const storageRef = ref(storage, `player-photos/${userId}/${claimId}/avatar.json`);

  await uploadBytes(storageRef, configBlob);
  const downloadURL = await getDownloadURL(storageRef);
  return downloadURL;
}

/**
 * Delete a player's photo from Firebase Storage
 * @param {number} userId - The user's ID
 * @param {number} claimId - The claim ID
 */
export async function deletePlayerPhoto(userId, claimId) {
  if (!isFirebaseConfigured()) {
    return;
  }

  try {
    // Try to delete common extensions
    const extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
    for (const ext of extensions) {
      try {
        const storageRef = ref(storage, `player-photos/${userId}/${claimId}/photo.${ext}`);
        await deleteObject(storageRef);
        console.log(`Deleted photo.${ext}`);
        break;
      } catch (e) {
        // File with this extension doesn't exist, try next
      }
    }
  } catch (error) {
    console.error('Error deleting photo:', error);
  }
}

/**
 * Compress an image before uploading
 * @param {File} file - The original image file
 * @param {number} maxWidth - Maximum width (default 800)
 * @param {number} quality - JPEG quality 0-1 (default 0.8)
 * @returns {Promise<Blob>} Compressed image blob
 */
export function compressImage(file, maxWidth = 800, quality = 0.8) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;

        // Calculate new dimensions
        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob);
            } else {
              reject(new Error('Failed to compress image'));
            }
          },
          'image/jpeg',
          quality
        );
      };
      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = event.target.result;
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
}

// Auth helper functions
export async function firebaseSignUp(email, password, displayName) {
  if (!auth) throw new Error('Firebase Auth not initialized');
  const userCredential = await createUserWithEmailAndPassword(auth, email, password);
  // Set display name
  if (displayName) {
    await updateProfile(userCredential.user, { displayName });
  }
  return userCredential.user;
}

export async function firebaseSignIn(email, password) {
  if (!auth) throw new Error('Firebase Auth not initialized');
  const userCredential = await signInWithEmailAndPassword(auth, email, password);
  return userCredential.user;
}

export async function firebaseSignOut() {
  if (!auth) throw new Error('Firebase Auth not initialized');
  await signOut(auth);
}

export async function firebaseResetPassword(email) {
  if (!auth) throw new Error('Firebase Auth not initialized');
  await sendPasswordResetEmail(auth, email);
}

export function onFirebaseAuthStateChanged(callback) {
  if (!auth) {
    console.warn('Firebase Auth not initialized');
    return () => {};
  }
  return onAuthStateChanged(auth, callback);
}

export { storage, auth };
