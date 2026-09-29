import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchVideoEvents } from '../api/api';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import ImageModal from '../components/ImageModal';

export default function AnalyticsView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);

  useEffect(() => {
    async function loadEvents() {
      try {
        const data = await fetchVideoEvents(id);
        setEvents(data);
      } catch (err) {
        setError('Failed to load timeline events. Make sure the video is completely processed.');
      } finally {
        setLoading(false);
      }
    }
    loadEvents();
  }, [id]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: '10rem' }}>
        <div className="spinner"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <button className="btn" style={{ backgroundColor: 'var(--bg-card)' }} onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> Back
        </button>
        <div className="card empty-state" style={{ marginTop: '2rem', color: 'var(--danger)' }}>
          {error}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
        <button className="btn" style={{ backgroundColor: 'var(--bg-card)' }} onClick={() => navigate(-1)}>
          <ArrowLeft size={16} />
        </button>
        <h1>Timeline Analytics — Video {id}</h1>
      </div>

      {events.length === 0 ? (
        <div className="card empty-state">No events recorded for this video.</div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: '2rem', height: 'clamp(260px, 40vw, 400px)', padding: '1rem 0.5rem 1rem 0' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={events} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#475569" vertical={false} />
                <XAxis 
                  dataKey="timestamp_sec" 
                  stroke="#94a3b8" 
                  tickFormatter={(val) => `${val}s`} 
                />
                <YAxis yAxisId="left" stroke="#3b82f6" label={{ value: 'Headcount', angle: -90, position: 'insideLeft', fill: '#94a3b8' }} />
                <YAxis yAxisId="right" orientation="right" stroke="#ef4444" label={{ value: 'Risk Score', angle: 90, position: 'insideRight', fill: '#94a3b8' }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '4px' }}
                  labelFormatter={(val) => `Time: ${val}s`}
                />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="headcount" stroke="#3b82f6" activeDot={{ r: 8 }} name="Headcount" strokeWidth={2} />
                <Line yAxisId="right" type="monotone" dataKey="risk_score" stroke="#ef4444" activeDot={{ r: 8 }} name="Risk Score (0-100)" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="card" style={{ padding: '0', overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time (sec)</th>
                  <th>Frame</th>
                  <th>Headcount</th>
                  <th>Speed (px/f)</th>
                  <th>Risk Score</th>
                  <th>Risk Level</th>
                  <th>Alert Image</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td className="font-mono">{ev.timestamp_sec.toFixed(2)}</td>
                    <td className="font-mono">{ev.frame_number}</td>
                    <td className="font-mono">{ev.headcount}</td>
                    <td className="font-mono">{ev.motion_speed.toFixed(3)}</td>
                    <td className="font-mono">{ev.risk_score}</td>
                    <td>
                      <span className={`badge ${ev.risk_level}`}>{ev.risk_level}</span>
                    </td>
                    <td>
                      {ev.alert_image_url ? (
                        <button 
                          className="btn" 
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                          onClick={() => setSelectedImage(ev)}
                        >
                          <ExternalLink size={14} /> View
                        </button>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {selectedImage && (
        <ImageModal event={selectedImage} onClose={() => setSelectedImage(null)} />
      )}
    </div>
  );
}
