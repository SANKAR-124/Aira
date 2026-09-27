const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function uploadVideo(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/videos/upload`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error('Failed to upload video');
  }
  
  return response.json();
}

export async function fetchVideos() {
  const response = await fetch(`${API_BASE_URL}/videos`);
  if (!response.ok) {
    throw new Error('Failed to fetch videos');
  }
  return response.json();
}

export async function fetchVideoEvents(videoId) {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}/events`);
  if (!response.ok) {
    throw new Error('Failed to fetch video events');
  }
  return response.json();
}

export async function fetchHighRiskAlerts() {
  const response = await fetch(`${API_BASE_URL}/alerts/high-risk`);
  if (!response.ok) {
    throw new Error('Failed to fetch high-risk alerts');
  }
  return response.json();
}

export async function deleteVideo(videoId) {
  const response = await fetch(`${API_BASE_URL}/videos/${videoId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete video');
  }
  return response.json();
}
