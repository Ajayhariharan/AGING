import React, { useState, useRef, useEffect } from 'react';
import { 
  X, UploadCloud, Layers, Trash2, CheckCircle2, Database, AlertTriangle, 
  Sun, Moon, Sparkles, Check, ArrowRight, Loader2
} from 'lucide-react';
import { uploadXlsbWithProgress, selectFile, deleteFile } from '../api';

export default function ControlPanel({
  isOpen,
  onClose,
  history,
  activeFileId,
  onRefresh,
  theme,
  onSetTheme,
  onToggleTheme
}) {
  const [selectedFileId, setSelectedFileId] = useState(activeFileId);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploadError, setUploadError] = useState(null);
  
  const [loadingFile, setLoadingFile] = useState(false);
  const [loadProgress, setLoadProgress] = useState(0);
  const [loadStatus, setLoadStatus] = useState('');

  const [dragActive, setDragActive] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (activeFileId) {
      setSelectedFileId(activeFileId);
    } else if (history.length > 0 && !selectedFileId) {
      setSelectedFileId(history[0].id);
    }
  }, [activeFileId, history]);

  const handleFileUpload = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.xlsb')) {
      setUploadError('Only .xlsb files are supported.');
      return;
    }
    setUploading(true);
    setUploadError(null);
    setUploadProgress(15);
    setUploadStatus('Reading .xlsb workbook...');
    
    try {
      await uploadXlsbWithProgress(file, (percent) => {
        setUploadProgress(Math.min(90, Math.max(20, percent)));
        setUploadStatus(`Uploading & Parsing (${percent}%)...`);
      });
      setUploadProgress(100);
      setUploadStatus('Storing sheets into SQLite DB...');
      setTimeout(() => {
        setUploading(false);
        setUploadProgress(0);
        onRefresh();
      }, 500);
    } catch (err) {
      setUploadError(err.message || 'Upload failed');
      setUploading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleLoadSelectedFile = async () => {
    if (!selectedFileId) return;
    setLoadingFile(true);
    setLoadProgress(20);
    setLoadStatus('Fetching tables from SQLite...');

    try {
      setLoadProgress(60);
      setLoadStatus('Loading dataset into high-speed memory cache...');
      await selectFile(selectedFileId);
      
      setLoadProgress(100);
      setLoadStatus('Data Loaded Successfully!');
      setTimeout(() => {
        setLoadingFile(false);
        setLoadProgress(0);
        onRefresh();
      }, 400);
    } catch (err) {
      console.error(err);
      setLoadingFile(false);
    }
  };

  const confirmDelete = async () => {
    if (!fileToDelete) return;
    setDeleting(true);
    try {
      await deleteFile(fileToDelete.id);
      if (selectedFileId === fileToDelete.id) {
        setSelectedFileId(null);
      }
      setFileToDelete(null);
      onRefresh();
    } catch (err) {
      console.error(err);
    } finally {
      setDeleting(false);
    }
  };

  const selectedFileObj = history.find(f => f.id === selectedFileId);

  return (
    <>
      {/* Drawer Backdrop */}
      <div 
        className={`drawer-backdrop ${isOpen ? 'open' : ''}`}
        onClick={onClose}
      />

      {/* Slide-In Drawer */}
      <aside className={`control-panel-drawer ${isOpen ? 'open' : ''}`}>
        {/* Drawer Header */}
        <div className="drawer-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Layers size={18} color="var(--accent-primary)" />
            <h2>Control Panel</h2>
          </div>
          <button 
            className="drawer-close-btn"
            onClick={onClose}
            title="Close Panel"
          >
            <X size={16} />
          </button>
        </div>

        {/* Database Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--tbl-bg)', border: '1px solid var(--tbl-border)', borderRadius: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Database size={14} color="var(--accent-primary)" />
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-main)' }}>Storage</span>
          </div>
          <span className="db-status-badge">
            <CheckCircle2 size={11} /> SQLite Connected
          </span>
        </div>

        {/* Upload New File Area */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-main)', textTransform: 'uppercase', marginBottom: 6 }}>
            Upload Workbook (.xlsb)
          </div>
          <div 
            className={`uploader-box ${dragActive ? 'drag-over' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => !uploading && fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept=".xlsb"
              onChange={(e) => handleFileUpload(e.target.files?.[0])}
            />
            <UploadCloud size={26} color="var(--accent-primary)" style={{ margin: '0 auto 4px auto' }} />
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-main)' }}>
              {uploading ? 'Processing & Storing...' : 'Click or Drag .xlsb here'}
            </div>
            <div style={{ fontSize: 10, color: 'var(--metric-label-color)', marginTop: 2 }}>
              Fast parsing & SQLite indexed storage
            </div>
          </div>

          {/* Upload Progress Bar */}
          {uploading && (
            <div className="progress-box">
              <div className="progress-header">
                <span>{uploadStatus}</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          )}

          {uploadError && (
            <div style={{ color: '#EF4444', fontSize: 11, fontWeight: 700, marginTop: 4 }}>
              {uploadError}
            </div>
          )}
        </div>

        {/* Upload History & File Selection */}
        <div className="history-section">
          <div className="history-section-header">
            <span>Select Workbook ({history.length})</span>
            <span style={{ fontSize: 10, color: 'var(--metric-label-color)', textTransform: 'none', fontWeight: 600 }}>
              Select & click Load below
            </span>
          </div>

          <div className="history-list">
            {history.length === 0 ? (
              <div style={{ fontSize: 11, color: 'var(--metric-label-color)', textAlign: 'center', padding: 14 }}>
                No workbooks uploaded yet.
              </div>
            ) : (
              history.map((file) => {
                const isSelected = file.id === selectedFileId;
                const isCurrentlyActive = file.id === activeFileId || file.is_active;

                return (
                  <div 
                    key={file.id} 
                    className={`history-card-selectable ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedFileId(file.id)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                        {/* Checkbox circle indicator */}
                        <div className="custom-radio-check">
                          {isSelected && <Check size={11} strokeWidth={3} />}
                        </div>

                        <span className="history-card-name" title={file.filename}>
                          {file.filename}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        {isCurrentlyActive && (
                          <span className="badge-active-file">Active</span>
                        )}
                        <button 
                          className="btn-icon-del"
                          title="Delete file from database"
                          onClick={(e) => {
                            e.stopPropagation();
                            setFileToDelete(file);
                          }}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>

                    <div className="history-card-meta" style={{ paddingLeft: 24 }}>
                      <span>{file.uploaded_at}</span>
                      <span>{file.total_rows?.toLocaleString()} rows</span>
                    </div>

                    {file.sheet_names && file.sheet_names.length > 0 && (
                      <div style={{ paddingLeft: 24, marginTop: 2 }}>
                        {file.sheet_names.map(s => (
                          <span key={s} className="sheet-badge">{s}</span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Load Progress Bar */}
          {loadingFile && (
            <div className="progress-box">
              <div className="progress-header">
                <span>{loadStatus}</span>
                <span>{loadProgress}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${loadProgress}%` }} />
              </div>
            </div>
          )}

          {/* Prominent Load Button at the bottom of the history section */}
          {history.length > 0 && (
            <button
              className="btn-load-file"
              disabled={loadingFile || !selectedFileId}
              onClick={handleLoadSelectedFile}
            >
              {loadingFile ? (
                <>
                  <Loader2 size={14} className="spin" />
                  <span>Loading Data...</span>
                </>
              ) : (
                <>
                  <span>Load Selected: <strong>{selectedFileObj?.filename || 'Workbook'}</strong></span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          )}
        </div>

        {/* Theme Mode Selector (Light, Dark, Dynamic) */}
        <div style={{ marginTop: 'auto', paddingTop: 8, borderTop: '1.5px solid var(--tbl-border)' }}>
          <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-main)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.3 }}>
            Appearance Theme
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 5 }}>
            <button 
              onClick={() => {
                if (onSetTheme) onSetTheme('light');
                else if (onToggleTheme) onToggleTheme('light');
              }}
              style={{
                background: theme === 'light' ? 'linear-gradient(135deg, #7C3AED, #6D28D9)' : 'var(--tab-nav-bg)',
                color: theme === 'light' ? '#FFFFFF' : 'var(--text-main)',
                border: theme === 'light' ? '1px solid #7C3AED' : '1px solid var(--tbl-border)',
                borderRadius: 8,
                padding: '6px 4px',
                fontSize: 11,
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
                boxShadow: theme === 'light' ? '0 2px 6px rgba(124, 58, 237, 0.25)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              <Sun size={12} color={theme === 'light' ? '#FFFFFF' : '#6D28D9'} />
              <span>Light</span>
              {theme === 'light' && <Check size={11} strokeWidth={3} />}
            </button>

            <button 
              onClick={() => {
                if (onSetTheme) onSetTheme('dark');
                else if (onToggleTheme) onToggleTheme('dark');
              }}
              style={{
                background: theme === 'dark' ? 'linear-gradient(135deg, #7C3AED, #6D28D9)' : 'var(--tab-nav-bg)',
                color: theme === 'dark' ? '#FFFFFF' : 'var(--text-main)',
                border: theme === 'dark' ? '1px solid #7C3AED' : '1px solid var(--tbl-border)',
                borderRadius: 8,
                padding: '6px 4px',
                fontSize: 11,
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
                boxShadow: theme === 'dark' ? '0 2px 6px rgba(124, 58, 237, 0.25)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              <Moon size={12} color={theme === 'dark' ? '#FFFFFF' : '#A855F7'} />
              <span>Dark</span>
              {theme === 'dark' && <Check size={11} strokeWidth={3} />}
            </button>

            <button 
              onClick={() => {
                if (onSetTheme) onSetTheme('dynamic');
                else if (onToggleTheme) onToggleTheme('dynamic');
              }}
              style={{
                background: theme === 'dynamic' ? 'linear-gradient(135deg, #1A946F, #114B5F)' : 'var(--tab-nav-bg)',
                color: theme === 'dynamic' ? '#FFFFFF' : 'var(--text-main)',
                border: theme === 'dynamic' ? '1px solid #1A946F' : '1px solid var(--tbl-border)',
                borderRadius: 8,
                padding: '6px 4px',
                fontSize: 11,
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
                boxShadow: theme === 'dynamic' ? '0 2px 6px rgba(26, 148, 111, 0.3)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              <Sparkles size={12} color={theme === 'dynamic' ? '#FFFFFF' : '#1A946F'} />
              <span>Dynamic</span>
              {theme === 'dynamic' && <Check size={11} strokeWidth={3} />}
            </button>
          </div>
        </div>
      </aside>

      {/* Custom React In-App Delete Modal */}
      {fileToDelete && (
        <div className="custom-modal-backdrop" onClick={() => !deleting && setFileToDelete(null)}>
          <div className="custom-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-icon-wrap">
                <AlertTriangle size={22} />
              </div>
              <h3>Delete File from Database?</h3>
            </div>

            <div className="modal-body">
              Are you sure you want to delete <strong>{fileToDelete.filename}</strong>?
              <p style={{ marginTop: 8, fontSize: 12, color: 'var(--metric-label-color)' }}>
                This will permanently remove all sheet tables and historical metrics associated with this file from SQLite database storage.
              </p>
            </div>

            <div className="modal-footer">
              <button 
                className="btn-modal-cancel"
                disabled={deleting}
                onClick={() => setFileToDelete(null)}
              >
                Cancel
              </button>
              <button 
                className="btn-modal-delete"
                disabled={deleting}
                onClick={confirmDelete}
              >
                {deleting ? 'Deleting...' : 'Delete File'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
