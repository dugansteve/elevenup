import { useState, useRef } from 'react';
import { isFirebaseConfigured, uploadPlayerPhoto, compressImage, deletePlayerPhoto } from '../config/firebase';

/**
 * Photo upload component with drag-and-drop, preview, and Firebase integration
 */
export default function PhotoUpload({
  userId,
  claimId,
  currentPhotoUrl,
  onPhotoUploaded,
  onPhotoRemoved
}) {
  const [preview, setPreview] = useState(currentPhotoUrl || null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const firebaseReady = isFirebaseConfigured();

  const handleFileSelect = async (file) => {
    if (!file) return;

    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      setError('Please upload a JPEG, PNG, GIF, or WebP image');
      return;
    }

    // Validate file size (max 5MB before compression)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image too large. Maximum size is 5MB');
      return;
    }

    setError(null);
    setUploading(true);

    try {
      // Compress image first
      const compressed = await compressImage(file, 800, 0.8);

      // Convert to data URL for preview and fallback storage
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(compressed);
      });

      // Show preview immediately
      setPreview(dataUrl);

      if (firebaseReady) {
        try {
          // Try to upload to Firebase
          const downloadUrl = await uploadPlayerPhoto(userId, claimId, compressed);
          if (onPhotoUploaded) {
            onPhotoUploaded(downloadUrl);
          }
        } catch (firebaseErr) {
          // Firebase upload failed - fall back to data URL
          console.warn('Firebase upload failed, using local storage:', firebaseErr.message);
          if (onPhotoUploaded) {
            onPhotoUploaded(dataUrl);
          }
        }
      } else {
        // Firebase not configured - use data URL
        console.warn('Firebase not configured. Photo stored locally.');
        if (onPhotoUploaded) {
          onPhotoUploaded(dataUrl);
        }
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'Failed to upload photo');
      setPreview(currentPhotoUrl || null);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleRemovePhoto = async () => {
    if (firebaseReady && currentPhotoUrl) {
      try {
        await deletePlayerPhoto(userId, claimId);
      } catch (err) {
        console.error('Error deleting photo:', err);
      }
    }
    setPreview(null);
    if (onPhotoRemoved) {
      onPhotoRemoved();
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <div style={styles.container}>
      <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => handleFileSelect(e.target.files[0])}
        accept="image/jpeg,image/png,image/gif,image/webp"
        style={{ display: 'none' }}
      />

      {preview ? (
        <div style={styles.previewContainer}>
          <img
            src={preview}
            alt="Player photo"
            style={styles.preview}
          />
          <div style={styles.previewActions}>
            <button
              onClick={triggerFileInput}
              style={styles.changeButton}
              disabled={uploading}
            >
              Change Photo
            </button>
            <button
              onClick={handleRemovePhoto}
              style={styles.removeButton}
              disabled={uploading}
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        <div
          style={{
            ...styles.dropzone,
            ...(dragOver && styles.dropzoneActive),
            ...(uploading && styles.dropzoneUploading)
          }}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={triggerFileInput}
        >
          {uploading ? (
            <div style={styles.uploadingState}>
              <div style={styles.spinner} />
              <span>Uploading...</span>
            </div>
          ) : (
            <>
              <div style={styles.uploadIcon}>📷</div>
              <div style={styles.dropzoneText}>
                <strong>Click to upload</strong> or drag and drop
              </div>
              <div style={styles.dropzoneHint}>
                JPEG, PNG, GIF or WebP (max 5MB)
              </div>
            </>
          )}
        </div>
      )}

      {error && <div style={styles.error}>{error}</div>}

      {!firebaseReady && (
        <div style={styles.warning}>
          Firebase not configured. Photos are stored locally only.
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    width: '100%',
  },
  dropzone: {
    border: '2px dashed #ccc',
    borderRadius: '12px',
    padding: '40px 20px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    backgroundColor: '#fafafa',
  },
  dropzoneActive: {
    borderColor: '#2d5016',
    backgroundColor: '#e8f5e9',
  },
  dropzoneUploading: {
    borderColor: '#1976d2',
    backgroundColor: '#e3f2fd',
    cursor: 'wait',
  },
  uploadIcon: {
    fontSize: '48px',
    marginBottom: '12px',
  },
  dropzoneText: {
    fontSize: '14px',
    color: '#333',
    marginBottom: '8px',
  },
  dropzoneHint: {
    fontSize: '12px',
    color: '#999',
  },
  uploadingState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
    color: '#1976d2',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid #e3f2fd',
    borderTop: '3px solid #1976d2',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  previewContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
  },
  preview: {
    width: '150px',
    height: '150px',
    borderRadius: '50%',
    objectFit: 'cover',
    border: '3px solid #2d5016',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
  },
  previewActions: {
    display: 'flex',
    gap: '8px',
  },
  changeButton: {
    padding: '8px 16px',
    backgroundColor: '#2d5016',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  removeButton: {
    padding: '8px 16px',
    backgroundColor: '#f5f5f5',
    color: '#c62828',
    border: '1px solid #c62828',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  error: {
    marginTop: '12px',
    padding: '10px',
    backgroundColor: '#ffebee',
    color: '#c62828',
    borderRadius: '6px',
    fontSize: '14px',
    textAlign: 'center',
  },
  warning: {
    marginTop: '12px',
    padding: '10px',
    backgroundColor: '#fff3e0',
    color: '#e65100',
    borderRadius: '6px',
    fontSize: '12px',
    textAlign: 'center',
  },
};

// Add CSS for spinner animation
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = `
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `;
  document.head.appendChild(styleSheet);
}
