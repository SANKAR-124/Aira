import { X } from 'lucide-react';

export default function ImageModal({ event, onClose }) {
  if (!event) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={e => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose} style={{ zIndex: 10, background: 'rgba(0,0,0,0.5)', padding: '0.25rem', borderRadius: '50%' }}>
          <X size={24} color="#fff" />
        </button>
        
        <div style={{ position: 'relative', width: '100%', backgroundColor: '#000', borderRadius: '4px', overflow: 'hidden' }}>
          <img 
            src={event.alert_image_url} 
            alt="High Risk Alert" 
            style={{ width: '100%', maxHeight: '75vh', objectFit: 'contain', display: 'block' }} 
          />
        </div>
        
        <div style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ marginBottom: '0.25rem' }}>High-Risk Alert Detected</h3>
            <p style={{ color: 'var(--text-muted)' }}>Timestamp: {event.timestamp_sec}s | Headcount: <span className="font-mono">{event.headcount}</span></p>
          </div>
          <div>
            <span className={`badge ${event.risk_level}`}>
              Risk Score: {event.risk_score} / 100
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
