// Unified API client for FastAPI backend

const API_BASE = '/api';

export function uploadXlsbWithProgress(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percent = Math.round((e.loaded / e.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve(data);
        } catch (err) {
          resolve(xhr.responseText);
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || 'Upload failed'));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    });

    xhr.addEventListener('error', () => reject(new Error('Network error during upload')));
    xhr.addEventListener('abort', () => reject(new Error('Upload aborted')));

    xhr.open('POST', `${API_BASE}/upload`);
    xhr.send(formData);
  });
}

export async function uploadXlsb(file) {
  return uploadXlsbWithProgress(file, null);
}

export async function getFilesHistory() {
  const res = await fetch(`${API_BASE}/files/history`);
  if (!res.ok) throw new Error('Failed to fetch file history');
  return res.json();
}

export async function selectFile(fileId) {
  const res = await fetch(`${API_BASE}/files/select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_id: fileId })
  });
  if (!res.ok) throw new Error('Failed to switch active file');
  return res.json();
}

export async function deleteFile(fileId) {
  const res = await fetch(`${API_BASE}/files/${fileId}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error('Failed to delete file');
  return res.json();
}

export async function getSheets() {
  const res = await fetch(`${API_BASE}/sheets`);
  if (!res.ok) throw new Error('Failed to fetch sheets');
  return res.json();
}

export async function getSheetData(sheetName, filters = {}, limit = 200, offset = 0) {
  const res = await fetch(`${API_BASE}/sheet-data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sheet_name: sheetName, filters, limit, offset })
  });
  if (!res.ok) throw new Error('Failed to fetch sheet data');
  return res.json();
}

export async function getDashboardData(week = [], branch = [], channel = []) {
  const res = await fetch(`${API_BASE}/dashboard`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ week, branch, channel })
  });
  if (!res.ok) throw new Error('Failed to fetch dashboard data');
  return res.json();
}

export async function getAlertsData(filters = {}) {
  const res = await fetch(`${API_BASE}/alerts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters)
  });
  if (!res.ok) throw new Error('Failed to fetch alerts data');
  return res.json();
}

export async function getComparisonData(filters = {}) {
  const res = await fetch(`${API_BASE}/comparison`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters)
  });
  if (!res.ok) throw new Error('Failed to fetch comparison data');
  return res.json();
}

export async function getTrendData(filters = {}) {
  const res = await fetch(`${API_BASE}/trend-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters)
  });
  if (!res.ok) throw new Error('Failed to fetch trend data');
  return res.json();
}
