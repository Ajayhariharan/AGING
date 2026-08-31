import React, { useState, useEffect } from 'react';
import { 
  SlidersHorizontal, UploadCloud, FileSpreadsheet
} from 'lucide-react';
import { getSheets, getFilesHistory } from './api';

import ControlPanel from './components/ControlPanel';
import RawSheetTab from './tabs/RawSheetTab';
import DashboardTab from './tabs/DashboardTab';
import AlertViewTab from './tabs/AlertViewTab';
import ComparisonTab from './tabs/ComparisonTab';

export default function App() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [sheetsInfo, setSheetsInfo] = useState({ loaded: false, filename: null, sheets: [] });
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [history, setHistory] = useState([]);
  const [activeFileId, setActiveFileId] = useState(null);
  const [isGlobalLoading, setIsGlobalLoading] = useState(false);

  // Theme Management (Light Purple / Dark Purple)
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('mdlz_theme') || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('mdlz_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const loadData = async () => {
    setIsGlobalLoading(true);
    try {
      const sheetsRes = await getSheets();
      setSheetsInfo(sheetsRes);
      if (sheetsRes.active_file_id) {
        setActiveFileId(sheetsRes.active_file_id);
      }
      const historyRes = await getFilesHistory();
      setHistory(historyRes.history || []);
      if (historyRes.active_file_id) {
        setActiveFileId(historyRes.active_file_id);
      }
    } catch (err) {
      console.error('Error loading initial data:', err);
    } finally {
      setTimeout(() => setIsGlobalLoading(false), 200);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Build full list of pill tab names
  const allTabs = [];
  if (sheetsInfo.loaded && sheetsInfo.sheets) {
    sheetsInfo.sheets.forEach(s => allTabs.push(s));
    allTabs.push('Dashboard');
    allTabs.push('Alert View');
    allTabs.push('Comparison');
  }

  return (
    <div className="app-container" data-theme={theme}>
      {/* Global Top Loading Progress Bar */}
      {isGlobalLoading && <div className="global-loading-bar" />}

      {/* ========================================================= */}
      {/* FIXED TOP HEADER (PINNED AT TOP, ZERO SCROLL)            */}
      {/* ========================================================= */}
      <header className="fixed-app-header">
        <div className="header-left-group">
          {/* Control Panel Toggle Button */}
          <button 
            className="control-panel-toggle-btn"
            onClick={() => setIsDrawerOpen(true)}
            title="Open Control Panel & File Manager"
          >
            <SlidersHorizontal size={14} />
            <span>Control Panel</span>
            {history.length > 0 && (
              <span style={{ background: 'var(--accent-primary)', color: '#fff', fontSize: 10, padding: '1px 6px', borderRadius: 10 }}>
                {history.length}
              </span>
            )}
          </button>

          <span className="header-title-text">Aging Dashboard</span>

          {sheetsInfo.loaded && sheetsInfo.filename && (
            <div className="active-file-header-pill" title={sheetsInfo.filename}>
              <FileSpreadsheet size={13} color="var(--accent-primary)" />
              <span>{sheetsInfo.filename}</span>
            </div>
          )}
        </div>

        {/* Pill Tab Navigation Bar pinned right in the header */}
        {sheetsInfo.loaded && (
          <nav className="header-tabs-nav">
            {allTabs.map(tab => (
              <button
                key={tab}
                className={`tab-pill ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </nav>
        )}
      </header>

      {/* ========================================================= */}
      {/* MODULAR CONTROL PANEL DRAWER                             */}
      {/* ========================================================= */}
      <ControlPanel 
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        history={history}
        activeFileId={activeFileId}
        onRefresh={loadData}
        theme={theme}
        onSetTheme={setTheme}
        onToggleTheme={setTheme}
      />

      {/* ========================================================= */}
      {/* MAIN CONTENT VIEWPORT (100% HEIGHT, ZERO SCROLL)          */}
      {/* ========================================================= */}
      <main className="main-content">
        {!sheetsInfo.loaded ? (
          <div style={{ background: 'var(--tbl-bg)', border: '1.5px solid var(--tbl-border)', borderRadius: 12, padding: 56, textAlign: 'center', marginTop: 30 }}>
            <UploadCloud size={54} color="#A855F7" style={{ margin: '0 auto 14px auto' }} />
            <h3 style={{ fontSize: 20, color: 'var(--text-main)', marginBottom: 8, fontWeight: 800 }}>Please upload an .xlsb inventory file to begin</h3>
            <p style={{ color: 'var(--metric-label-color)', fontSize: 14, marginBottom: 20 }}>
              Click on the <strong>Control Panel</strong> button at the top left to upload your .xlsb file or select a file from history.
            </p>
            <button className="btn-primary" onClick={() => setIsDrawerOpen(true)}>
              <SlidersHorizontal size={16} /> Open Control Panel
            </button>
          </div>
        ) : (
          <div className="active-tab-wrapper">
            {/* key={activeFileId} guarantees instant reactive update across all tabs upon loading a file */}
            {activeTab === 'Dashboard' && <DashboardTab key={`dash_${activeFileId}`} theme={theme} />}
            {activeTab === 'Alert View' && <AlertViewTab key={`alert_${activeFileId}`} theme={theme} />}
            {activeTab === 'Comparison' && <ComparisonTab key={`comp_${activeFileId}`} theme={theme} />}
            {sheetsInfo.sheets.includes(activeTab) && <RawSheetTab key={`raw_${activeFileId}_${activeTab}`} sheetName={activeTab} />}
          </div>
        )}
      </main>
    </div>
  );
}
