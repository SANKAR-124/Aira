import { UploadCloud, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Topbar({ onUploadClick }) {
  const navigate = useNavigate();

  return (
    <header className="topbar">
      <div 
        className="topbar-title" 
        onClick={() => navigate('/')}
        style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}
      >
        <ShieldAlert size={28} color="#3b82f6" />
        AIRA / RCMP Security Console
      </div>
      <button className="btn" onClick={onUploadClick}>
        <UploadCloud size={20} />
        Upload Video
      </button>
    </header>
  );
}
