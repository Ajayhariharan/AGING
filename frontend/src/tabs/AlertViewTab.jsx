import React, { useState, useEffect } from 'react';
import { getAlertsData } from '../api';
import { Download } from 'lucide-react';

export default function AlertViewTab() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  
  const [selectedDepot, setSelectedDepot] = useState([]);
  const [selectedBrand, setSelectedBrand] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState([]);
  const [selectedRisk, setSelectedRisk] = useState(['High (20-50%)', 'Medium (50-75%)']);
  const [selectedCategory, setSelectedCategory] = useState([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getAlertsData({
        depot: selectedDepot,
        brand: selectedBrand,
        channel: selectedChannel,
        risk: selectedRisk,
        category: selectedCategory
      });
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedDepot, selectedBrand, selectedChannel, selectedRisk, selectedCategory]);

  const downloadCSV = () => {
    if (!data?.alerts || data.alerts.length === 0) return;
    const headers = ['SKU Description', 'Brand', 'Shelf Life Left', 'Est. Days', 'Stock (Cases)', 'Value (Cr)', 'Risk', 'Action'];
    const rows = data.alerts.map(a => [
      `"${a.sku_description.replace(/"/g, '""')}"`,
      `"${a.brand.replace(/"/g, '""')}"`,
      `"${a.shelf_life_left}"`,
      a.est_days ?? '',
      a.stock_cases,
      a.value_cr,
      a.risk,
      `"${a.action.replace(/"/g, '""')}"`
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "shelf_life_alerts.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading && !data) {
    return <div style={{ padding: 20, textAlign: 'center', color: '#6B21A8', fontSize: 13 }}>Loading Shelf-Life Alerts...</div>;
  }

  if (!data) {
    return <div style={{ padding: 20, fontSize: 13 }}>No stock data available for Alerts.</div>;
  }

  const { filters, kpis, alerts } = data;

  return (
    <div className="tab-view-container">
      {/* Filters Bar */}
      <div className="filter-bar">
        <div className="filter-group">
          <label>Depot:</label>
          <select 
            className="custom-select"
            value={selectedDepot[0] || ''}
            onChange={(e) => setSelectedDepot(e.target.value ? [e.target.value] : [])}
          >
            <option value="">All Depots</option>
            {filters?.depot_options?.map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Brand:</label>
          <select 
            className="custom-select"
            value={selectedBrand[0] || ''}
            onChange={(e) => setSelectedBrand(e.target.value ? [e.target.value] : [])}
          >
            <option value="">All Brands</option>
            {filters?.brand_options?.map(b => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Channel:</label>
          <select 
            className="custom-select"
            value={selectedChannel[0] || ''}
            onChange={(e) => setSelectedChannel(e.target.value ? [e.target.value] : [])}
          >
            <option value="">All Channels</option>
            {filters?.channel_options?.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Risk Level:</label>
          <select 
            className="custom-select"
            value={selectedRisk.length === 1 ? selectedRisk[0] : ''}
            onChange={(e) => setSelectedRisk(e.target.value ? [e.target.value] : ['High (20-50%)', 'Medium (50-75%)'])}
          >
            <option value="">All (High & Medium)</option>
            {filters?.risk_options?.map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Category:</label>
          <select 
            className="custom-select"
            value={selectedCategory[0] || ''}
            onChange={(e) => setSelectedCategory(e.target.value ? [e.target.value] : [])}
          >
            <option value="">All Categories</option>
            {filters?.category_options?.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <button onClick={downloadCSV} className="btn-primary">
          <Download size={13} /> Export CSV
        </button>
      </div>

      {/* 4 Metric Cards in Crores */}
      <div className="kpi-grid-4">
        <div className="metric-card">
          <div className="metric-label">High Risk Exposure (20-50%)</div>
          <div className="metric-value" style={{ color: '#991B1B' }}>₹{Number(kpis.high_risk_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Medium Risk Exposure (50-75%)</div>
          <div className="metric-value" style={{ color: '#D97706' }}>₹{Number(kpis.medium_risk_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">High Risk SKUs</div>
          <div className="metric-value">{kpis.high_risk_skus}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Medium Risk SKUs</div>
          <div className="metric-value">{kpis.medium_risk_skus}</div>
        </div>
      </div>

      {/* Styled Alerts Table - Expands to Fill Bottom */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <h3 className="section-header">Shelf-Life Risk Alerts & Prescribed Actions</h3>
        <div className="table-wrapper" style={{ background: 'var(--tbl-bg)' }}>
          <table className="styled-table">
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>SKU Description</th>
                <th style={{ textAlign: 'left' }}>Brand</th>
                <th style={{ textAlign: 'center' }}>Shelf Life Left</th>
                <th style={{ textAlign: 'right' }}>Est. Days</th>
                <th style={{ textAlign: 'right' }}>Stock (Cases)</th>
                <th style={{ textAlign: 'right' }}>Value (Cr)</th>
                <th style={{ textAlign: 'center' }}>Risk</th>
                <th style={{ textAlign: 'left' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {alerts?.map((a, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, textAlign: 'left' }}>{a.sku_description}</td>
                  <td style={{ textAlign: 'left' }}>{a.brand}</td>
                  <td style={{ textAlign: 'center' }}>{a.shelf_life_left}</td>
                  <td style={{ textAlign: 'right' }}>{a.est_days ?? '-'}</td>
                  <td style={{ textAlign: 'right' }}>{a.stock_cases?.toLocaleString()}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>₹{Number(a.value_cr || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr</td>
                  <td style={{ textAlign: 'center' }}>
                    <span className={a.risk === 'High' ? 'badge-high' : 'badge-medium'}>
                      {a.risk}
                    </span>
                  </td>
                  <td style={{ textAlign: 'left', fontWeight: 600, color: 'var(--text-main)' }}>{a.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
