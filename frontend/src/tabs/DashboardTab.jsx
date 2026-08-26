import React, { useState, useEffect } from 'react';
import { getDashboardData } from '../api';

export default function DashboardTab() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedWeek, setSelectedWeek] = useState([]);
  const [selectedBranch, setSelectedBranch] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getDashboardData(selectedWeek, selectedBranch, selectedChannel);
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedWeek, selectedBranch, selectedChannel]);

  if (loading && !data) {
    return <div style={{ padding: 20, textAlign: 'center', color: '#6B21A8', fontSize: 13 }}>Loading Dashboard metrics...</div>;
  }

  if (!data) {
    return <div style={{ padding: 20, fontSize: 13 }}>No stock data available for the dashboard.</div>;
  }

  const { filters, risk_cards, category_table, branch_category_pivot, brand_table, branch_table, heatmap } = data;

  const getHeatmapStyle = (val, min, max) => {
    if (!val || val === 0) {
      return {
        bg: 'transparent',
        color: 'var(--text-body)',
        fontWeight: 400
      };
    }
    const ratio = Math.min(1, Math.max(0, (val - min) / (max - min || 1)));
    if (ratio < 0.25) {
      return {
        bg: 'rgba(234, 179, 8, 0.28)',
        color: 'var(--text-main)',
        fontWeight: 700
      };
    }
    if (ratio < 0.55) {
      return {
        bg: 'rgba(249, 115, 22, 0.65)',
        color: '#FFFFFF',
        fontWeight: 700
      };
    }
    if (ratio < 0.8) {
      return {
        bg: 'rgba(239, 68, 68, 0.82)',
        color: '#FFFFFF',
        fontWeight: 700
      };
    }
    return {
      bg: 'rgba(220, 38, 38, 0.95)',
      color: '#FFFFFF',
      fontWeight: 800
    };
  };

  return (
    <div className="tab-view-container">
      {/* Slicers Bar */}
      <div className="filter-bar">
        <div className="filter-group">
          <label>Week:</label>
          <select 
            className="custom-select"
            value={selectedWeek[0] || ''}
            onChange={(e) => setSelectedWeek(e.target.value ? [e.target.value] : [])}
          >
            <option value="">All Weeks</option>
            {filters?.week_options?.map(w => (
              <option key={w} value={w}>{w}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Branch:</label>
          <select 
            className="custom-select"
            value={selectedBranch[0] || ''}
            onChange={(e) => setSelectedBranch(e.target.value ? [e.target.value] : [])}
          >
            <option value="">All Branches</option>
            {filters?.branch_options?.map(b => (
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
      </div>

      {/* 2 High/Medium Risk Cards */}
      <div className="kpi-grid-2">
        <div className="risk-card-high">
          <div>
            <h4>HIGH RISK</h4>
            <div className="risk-card-sub">Total amount in Crores (20%-50%)</div>
          </div>
          <div className="risk-card-val">₹{risk_cards?.high_risk_cr?.toFixed(2)} Cr</div>
        </div>

        <div className="risk-card-med">
          <div>
            <h4>MEDIUM RISK</h4>
            <div className="risk-card-sub">Total amount in Crores (50%-75%)</div>
          </div>
          <div className="risk-card-val">₹{risk_cards?.med_risk_cr?.toFixed(2)} Cr</div>
        </div>
      </div>

      {/* Middle 2-Column Section (Hugs table content tightly - ZERO empty space voids) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, flexShrink: 0 }}>
        {/* Left Column: Category & Branch x Category */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div>
            <h3 className="section-header">AT-RISK BY CATEGORY (CR)</h3>
            <div className="table-wrapper" style={{ flex: 'none', height: 'auto', maxHeight: 'none', background: 'var(--tbl-bg)' }}>
              <table className="styled-table">
                <thead>
                  <tr>
                    {category_table.columns.map(c => (
                      <th key={c} style={{ textAlign: c === 'Category' ? 'left' : 'right' }}>
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {category_table.rows.map((r, i) => {
                    const isTotal = String(r['Category'] || '').toLowerCase() === 'total';
                    return (
                      <tr key={i} className={isTotal ? 'total-row' : ''}>
                        {category_table.columns.map(c => (
                          <td key={c} style={{ textAlign: c === 'Category' ? 'left' : 'right' }}>
                            {typeof r[c] === 'number' ? r[c].toFixed(2) : r[c]}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3 className="section-header">AT-RISK BY BRANCH x CATEGORY (CR)</h3>
            <div className="table-wrapper" style={{ flex: 'none', height: 'auto', maxHeight: 'none', background: 'var(--tbl-bg)' }}>
              <table className="styled-table">
                <thead>
                  <tr>
                    {branch_category_pivot.columns.map(c => (
                      <th key={c} style={{ textAlign: c === 'Branch' ? 'left' : 'right' }}>
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {branch_category_pivot.rows.map((r, i) => {
                    const isTotal = String(r['Branch'] || '').toLowerCase() === 'total';
                    return (
                      <tr key={i} className={isTotal ? 'total-row' : ''}>
                        {branch_category_pivot.columns.map(c => (
                          <td key={c} style={{ textAlign: c === 'Branch' ? 'left' : 'right' }}>
                            {typeof r[c] === 'number' ? r[c].toFixed(2) : r[c]}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: Top 10 Brands & Branch */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div>
            <h3 className="section-header">TOP 10 BRANDS (CR)</h3>
            <div className="table-wrapper" style={{ flex: 'none', height: 'auto', maxHeight: 'none', background: 'var(--tbl-bg)' }}>
              <table className="styled-table">
                <thead>
                  <tr>
                    {brand_table.columns.map(c => (
                      <th key={c} style={{ textAlign: (c === '#' || c === 'Brand') ? 'left' : 'right' }}>
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {brand_table.rows.map((r, i) => {
                    const isTotal = String(r['Brand'] || '').toLowerCase() === 'total';
                    return (
                      <tr key={i} className={isTotal ? 'total-row' : ''}>
                        {brand_table.columns.map(c => (
                          <td key={c} style={{ textAlign: (c === '#' || c === 'Brand') ? 'left' : 'right' }}>
                            {typeof r[c] === 'number' ? r[c].toFixed(2) : r[c]}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3 className="section-header">AT-RISK BY BRANCH (CR)</h3>
            <div className="table-wrapper" style={{ flex: 'none', height: 'auto', maxHeight: 'none', background: 'var(--tbl-bg)' }}>
              <table className="styled-table">
                <thead>
                  <tr>
                    {branch_table.columns.map(c => (
                      <th key={c} style={{ textAlign: c === 'Branch' ? 'left' : 'right' }}>
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {branch_table.rows.map((r, i) => {
                    const isTotal = String(r['Branch'] || '').toLowerCase() === 'total';
                    return (
                      <tr key={i} className={isTotal ? 'total-row' : ''}>
                        {branch_table.columns.map(c => (
                          <td key={c} style={{ textAlign: c === 'Branch' ? 'left' : 'right' }}>
                            {typeof r[c] === 'number' ? r[c].toFixed(2) : r[c]}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section: DC Heatmap Table (Expands to fill remaining viewport height) */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <h3 className="section-header">IWO REBALANCING - NEAR-AGEING STOCK BY DC (CR)</h3>
        <div className="table-wrapper" style={{ flex: 1, minHeight: 0, height: '100%', background: 'var(--tbl-bg)' }}>
          <table className="styled-table">
            <thead>
              <tr>
                {heatmap.columns.map((c, idx) => (
                  <th 
                    key={c} 
                    style={{ 
                      textAlign: c === 'LINK DES' ? 'left' : 'right',
                      position: 'sticky',
                      left: idx === 0 ? 0 : 'auto',
                      zIndex: idx === 0 ? 20 : 10,
                      background: 'var(--tbl-hdr-bg)',
                      color: 'var(--tbl-hdr-text)'
                    }}
                  >
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {heatmap.rows.map((r, i) => (
                <tr key={i}>
                  <td 
                    style={{ 
                      fontWeight: 700, 
                      textAlign: 'left',
                      position: 'sticky',
                      left: 0,
                      backgroundColor: 'var(--tbl-bg)',
                      color: 'var(--text-main)',
                      zIndex: 5,
                      borderRight: '2px solid var(--tbl-border)'
                    }}
                  >
                    {r['LINK DES']}
                  </td>
                  {heatmap.columns.slice(1).map(dep => {
                    const val = r[dep];
                    const cellStyle = getHeatmapStyle(val, heatmap.min_val, heatmap.max_val);
                    return (
                      <td 
                        key={dep} 
                        style={{ 
                          textAlign: 'right', 
                          backgroundColor: cellStyle.bg, 
                          color: cellStyle.color,
                          fontWeight: cellStyle.fontWeight
                        }}
                      >
                        {typeof val === 'number' ? val.toFixed(2) : val}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
