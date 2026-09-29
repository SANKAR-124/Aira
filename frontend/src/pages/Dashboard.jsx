import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchVideos, fetchHighRiskAlerts, deleteVideo } from '../api/api';
import ImageModal from '../components/ImageModal';
import { Video, AlertTriangle, Trash2 } from 'lucide-react';

export default function Dashboard() {
  const [videos, setVideos] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    async function loadData() {
      try {
        const [videoData, alertData] = await Promise.all([
          fetchVideos(),
          fetchHighRiskAlerts()
        ]);
        setVideos(videoData);
        setAlerts(alertData);
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
    
    // Auto-refresh every 3 seconds for live updates on video processing
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (e, videoId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this failed video and its data?")) return;
    
    try {
      await deleteVideo(videoId);
      // Immediately refresh data
      const [videoData, alertData] = await Promise.all([
        fetchVideos(),
        fetchHighRiskAlerts()
      ]);
      setVideos(videoData);
      setAlerts(alertData);
    } catch (err) {
      console.error("Failed to delete video:", err);
      alert("Failed to delete video.");
    }
  };

  if (loading && videos.length === 0) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: '10rem' }}>
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>Overview</h1>
      
      <div className="grid-layout">
        <section>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <AlertTriangle color="var(--danger)" />
            <h2>Recent High-Risk Alerts</h2>
          </div>
          
          {alerts.length === 0 ? (
            <div className="card empty-state">
              <p>No high-risk alerts detected recently.</p>
            </div>
          ) : (
            <div className="alerts-grid">
              {alerts.map(alert => (
                <div key={alert.id} className="alert-card" onClick={() => setSelectedAlert(alert)}>
                  <div className="alert-image-wrapper">
                    <img
                      src={alert.alert_image_url}
                      alt="Alert heatmap"
                      loading="lazy"
                      onError={e => {
                        e.target.onerror = null;
                        e.target.style.display = 'none';
                        e.target.parentNode.style.background = '#1e293b';
                      }}
                    />
                  </div>
                  <div className="alert-info">
                    <span className="font-mono text-sm">{alert.timestamp_sec}s</span>
                    <span className={`badge ${alert.risk_level}`}>
                      {alert.risk_level}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Video color="var(--accent)" />
            <h2>Processed Videos</h2>
          </div>
          
          <div className="card" style={{ padding: '1rem' }}>
            {videos.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem 0' }}>
                No videos uploaded yet.
              </p>
            ) : (
              <div className="video-list">
                {videos.map(video => (
                  <div 
                    key={video.id} 
                    className="video-item" 
                    onClick={() => {
                      if (video.processed_status === 'completed') {
                        navigate(`/videos/${video.id}`);
                      }
                    }}
                    style={{ cursor: video.processed_status === 'completed' ? 'pointer' : 'default' }}
                  >
                  <div>
                    <div className="video-item-name">{video.original_filename}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {new Date(video.created_at).toLocaleString()}
                    </div>
                  </div>
                    <div className="status-indicator" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className={`dot ${video.processed_status}`}></span>
                        <span style={{ textTransform: 'capitalize' }}>{video.processed_status}</span>
                      </div>
                      
                      {video.processed_status === 'failed' && (
                        <button 
                          onClick={(e) => handleDelete(e, video.id)}
                          style={{
                            background: 'transparent', border: 'none', 
                            color: 'var(--danger)', cursor: 'pointer',
                            padding: '4px'
                          }}
                          title="Delete failed video"
                        >
                          <Trash2 size={18} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      {selectedAlert && (
        <ImageModal event={selectedAlert} onClose={() => setSelectedAlert(null)} />
      )}
    </div>
  );
}
