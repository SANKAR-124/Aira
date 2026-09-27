import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import AnalyticsView from './pages/AnalyticsView';
import Topbar from './components/Topbar';
import { useState } from 'react';
import UploadModal from './components/UploadModal';

function App() {
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  return (
    <Router>
      <div className="app-container">
        <Topbar onUploadClick={() => setIsUploadOpen(true)} />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/videos/:id" element={<AnalyticsView />} />
          </Routes>
        </main>
        
        {isUploadOpen && (
          <UploadModal onClose={() => setIsUploadOpen(false)} />
        )}
      </div>
    </Router>
  );
}

export default App;
