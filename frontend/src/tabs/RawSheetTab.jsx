import React, { useState, useEffect } from 'react';
import { getSheetData } from '../api';

export default function RawSheetTab({ sheetName }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedFilters, setSelectedFilters] = useState({});
  const [offset, setOffset] = useState(0);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getSheetData(sheetName, selectedFilters, 200, offset);
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [sheetName, selectedFilters, offset]);

  if (loading && !data) {
    return <div style={{ padding: 20, textAlign: 'center', color: '#6B21A8', fontSize: 13 }}>Loading sheet data...</div>;
  }

  if (!data) {
    return <div style={{ padding: 20, fontSize: 13 }}>No sheet data available.</div>;
  }

  const { kpis, is_master, filter_options, columns, total_rows, data: rows } = data;

  return (
    <div className="tab-view-container">
      {/* Filter Row */}
      {filter_options && Object.keys(filter_options).length > 0 && (
        <div className="filter-bar">
          {Object.entries(filter_options).map(([col, options]) => (
            <div key={col} className="filter-group">
              <label>{col}:</label>
              <select
                className="custom-select"
                value={(selectedFilters[col] && selectedFilters[col][0]) || ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedFilters(prev => ({
                    ...prev,
                    [col]: val ? [val] : []
                  }));
                }}
              >
                <option value="">All ({options.length})</option>
                {options.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}

      {/* KPI Cards */}
      <div className="kpi-grid-4">
        <div className="metric-card">
          <div className="metric-label">Rows</div>
          <div className="metric-value">{kpis.rows?.toLocaleString() || 0}</div>
        </div>
        {is_master ? (
          <>
            <div className="metric-card">
              <div className="metric-label">Unique Materials</div>
              <div className="metric-value">{kpis.unique_materials || 0}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Unique Depots</div>
              <div className="metric-value">{kpis.unique_depots || 0}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Unique Categories</div>
              <div className="metric-value">{kpis.unique_categories || 0}</div>
            </div>
          </>
        ) : (
          <>
            <div className="metric-card">
              <div className="metric-label">Total Stock (Cases)</div>
              <div className="metric-value">{kpis.total_stock?.toLocaleString() || 0}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Total Value in Crores (Cr)</div>
              <div className="metric-value">₹{kpis.amount_crores?.toFixed(2) || '0.00'} Cr</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">SKUs</div>
              <div className="metric-value">{kpis.skus || 0}</div>
            </div>
          </>
        )}
      </div>

      {/* Styled Table - Expands to Fill Bottom */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div className="table-wrapper">
          <table className="styled-table">
            <thead>
              <tr>
                {columns.map(col => (
                  <th key={col} style={{ textAlign: (col.includes('Stock') || col.includes('Cr') || col.includes('Value')) ? 'right' : 'left' }}>
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  {columns.map(col => (
                    <td key={col} style={{ textAlign: (typeof r[col] === 'number' || (typeof r[col] === 'string' && r[col].endsWith('%'))) ? 'right' : 'left' }}>
                      {r[col]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
