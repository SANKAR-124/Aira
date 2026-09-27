import { useState } from 'react';
import { X, Upload } from 'lucide-react';
import { uploadVideo } from '../api/api';

export default function UploadModal({ onClose }) {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setError('');
    
    try {
      await uploadVideo(file);
      setSuccess('Video uploaded. Processing started.');
      // Wait a moment then close
      setTimeout(() => {
        onClose();
        // optionally trigger a refresh of the video list via global state or reload
        window.location.reload(); 
      }, 2000);
    } catch (err) {
      setError(err.message || 'Failed to upload video');
      setIsUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>
          <X size={24} />
        </button>
        
        <h2>Upload Video for Analysis</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', marginTop: '0.5rem' }}>
          Select an MP4 or AVI file from your CCTV cameras.
        </p>

        {success ? (
          <div style={{ backgroundColor: 'var(--success)', padding: '1rem', borderRadius: '4px', textAlign: 'center' }}>
            {success}
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <label className="dropzone" style={{ display: 'block' }}>
              <input 
                type="file" 
                accept="video/mp4,video/avi" 
                style={{ display: 'none' }}
                onChange={handleFileChange}
              />
              <Upload size={48} style={{ margin: '0 auto', color: 'var(--accent)', marginBottom: '1rem' }} />
              {file ? (
                <div style={{ fontWeight: 'bold' }}>{file.name}</div>
              ) : (
                <div>Click to select or drag and drop video file</div>
              )}
            </label>

            {error && <div style={{ color: 'var(--danger)', marginBottom: '1rem' }}>{error}</div>}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
              <button type="button" className="btn" style={{ backgroundColor: 'var(--primary)' }} onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn" disabled={!file || isUploading}>
                {isUploading ? 'Uploading...' : 'Upload & Analyze'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
