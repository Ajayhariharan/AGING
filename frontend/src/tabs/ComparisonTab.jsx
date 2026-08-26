import React, { useState, useEffect, useRef } from 'react';
import { getComparisonData } from '../api';
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid 
} from 'recharts';
import { ChevronDown, Check } from 'lucide-react';

export default function ComparisonTab() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  
  // Comparison Mode: 'weekly' (within file), 'monthly' (multi-month), 'yearly' (annual)
  const [mode, setMode] = useState('weekly');
  
  const [selectedWeeks, setSelectedWeeks] = useState([]);
  const [selectedBranches, setSelectedBranches] = useState([]);
  const [selectedChannels, setSelectedChannels] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedBrands, setSelectedBrands] = useState([]);

  // Multi-select dropdown open state
  const [isMonthDropdownOpen, setIsMonthDropdownOpen] = useState(false);
  const monthDropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (monthDropdownRef.current && !monthDropdownRef.current.contains(event.target)) {
        setIsMonthDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getComparisonData({
        mode,
        weeks: selectedWeeks,
        branches: selectedBranches,
        channels: selectedChannels,
        categories: selectedCategories,
        brands: selectedBrands
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
  }, [mode, selectedWeeks, selectedBranches, selectedChannels, selectedCategories, selectedBrands]);

  if (loading && !data) {
    return <div style={{ padding: 20, textAlign: 'center', color: '#6B21A8', fontSize: 13 }}>Loading Comparison metrics...</div>;
  }

  if (!data) {
    return <div style={{ padding: 20, fontSize: 13 }}>No comparison data available.</div>;
  }

  const { filters, kpis, charts, matrices } = data;
  const isWeekly = mode === 'weekly';
  const activePeriodsList = filters?.active_weeks || [];
  const allAvailablePeriods = filters?.week_options || [];

  // Toggle multi-select months in monthly comparison mode
  const toggleMonthSelection = (m) => {
    if (selectedWeeks.includes(m)) {
      const next = selectedWeeks.filter(x => x !== m);
      setSelectedWeeks(next);
    } else {
      setSelectedWeeks([...selectedWeeks, m]);
    }
  };

  const selectAllMonths = () => {
    setSelectedWeeks([]);
  };

  // Label for the month multi-select dropdown button
  const getMonthDropdownLabel = () => {
    if (selectedWeeks.length === 0 || selectedWeeks.length === allAvailablePeriods.length) {
      return `All Months (${allAvailablePeriods.length})`;
    }
    if (selectedWeeks.length === 1) {
      return selectedWeeks[0];
    }
    return `${selectedWeeks.length} Months Selected`;
  };

  // =========================================================================
  // DATA MAPPINGS FOR CHARTS
  // =========================================================================

  // 1. Weekly Chart 1: Category on X-axis, Grouped by Week
  const weeklyCatMap = {};
  charts?.cat_evolution?.forEach(item => {
    if (!weeklyCatMap[item.category]) weeklyCatMap[item.category] = { category: item.category };
    weeklyCatMap[item.category][item.week] = item.value_cr;
  });
  const weeklyCatChartData = Object.values(weeklyCatMap);

  // Monthly Chart 1: Period on X-axis, Line/Bar per Category
  const monthlyCatMap = {};
  const catNamesSet = new Set();
  charts?.cat_evolution?.forEach(item => {
    if (!monthlyCatMap[item.week]) monthlyCatMap[item.week] = { period: item.week };
    monthlyCatMap[item.week][item.category] = item.value_cr;
    catNamesSet.add(item.category);
  });
  const monthlyCatChartData = Object.values(monthlyCatMap);
  const catNames = Array.from(catNamesSet);

  // 2. Weekly Chart 2: Week on X-axis, Stacked by Bucket %
  const weeklyBucketMap = {};
  const allBucketsOrder = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75', '75 to 80', '80 to 85'];
  charts?.bucket_migration?.forEach(item => {
    if (!weeklyBucketMap[item.week]) weeklyBucketMap[item.week] = { week: item.week };
    weeklyBucketMap[item.week][item.bucket] = item.value_cr;
  });
  const weeklyBucketChartData = Object.values(weeklyBucketMap);

  // Monthly Chart 2: Period on X-axis, Line/Bar per Bucket
  const monthlyBucketMap = {};
  const bucketNamesSet = new Set();
  charts?.bucket_migration?.forEach(item => {
    if (!monthlyBucketMap[item.week]) monthlyBucketMap[item.week] = { period: item.week };
    monthlyBucketMap[item.week][item.bucket] = item.value_cr;
    bucketNamesSet.add(item.bucket);
  });
  const monthlyBucketChartData = Object.values(monthlyBucketMap);
  const bucketNames = Array.from(bucketNamesSet);

  // 3. Chart 3: Branch on X-axis, Grouped by Period/Week
  const branchDataMap = {};
  charts?.branch_comparison?.forEach(item => {
    if (!branchDataMap[item.branch]) branchDataMap[item.branch] = { branch: item.branch };
    branchDataMap[item.branch][item.week] = item.value_cr;
  });
  const branchChartData = Object.values(branchDataMap);

  const colors = ['#7C3AED', '#EC4899', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#14B8A6'];
  const bucketColors = ['#EF4444', '#F97316', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#6366F1'];

  return (
    <div className="tab-view-container">
      {/* Top Slicers & Mode Selection Bar */}
      <div className="filter-bar">
        {/* Mode Selector Toggle */}
        <div className="filter-group" style={{ flex: '0 0 auto' }}>
          <label>Compare By:</label>
          <div style={{ display: 'inline-flex', background: 'var(--tab-nav-bg)', borderRadius: 8, padding: 2, border: '1px solid var(--tbl-border)' }}>
            <button
              onClick={() => { setMode('weekly'); setSelectedWeeks([]); }}
              style={{
                background: mode === 'weekly' ? 'linear-gradient(135deg, #7C3AED, #6D28D9)' : 'transparent',
                color: mode === 'weekly' ? '#fff' : 'var(--text-main)',
                border: 'none',
                borderRadius: 6,
                padding: '3px 9px',
                fontSize: 11,
                fontWeight: 800,
                cursor: 'pointer'
              }}
            >
              Weekly
            </button>
            <button
              onClick={() => { setMode('monthly'); setSelectedWeeks([]); }}
              style={{
                background: mode === 'monthly' ? 'linear-gradient(135deg, #7C3AED, #6D28D9)' : 'transparent',
                color: mode === 'monthly' ? '#fff' : 'var(--text-main)',
                border: 'none',
                borderRadius: 6,
                padding: '3px 9px',
                fontSize: 11,
                fontWeight: 800,
                cursor: 'pointer'
              }}
            >
              Monthly Comparison
            </button>
            <button
              onClick={() => { setMode('yearly'); setSelectedWeeks([]); }}
              style={{
                background: mode === 'yearly' ? 'linear-gradient(135deg, #7C3AED, #6D28D9)' : 'transparent',
                color: mode === 'yearly' ? '#fff' : 'var(--text-main)',
                border: 'none',
                borderRadius: 6,
                padding: '3px 9px',
                fontSize: 11,
                fontWeight: 800,
                cursor: 'pointer'
              }}
            >
              Yearly
            </button>
          </div>
        </div>

        {/* Periods / Weeks Slicer: Multi-Select Checkbox Dropdown for Monthly or Select Dropdown for Weekly */}
        {mode === 'monthly' ? (
          <div className="filter-group" ref={monthDropdownRef}>
            <label>Months:</label>
            <div className="custom-multiselect-container">
              <button
                type="button"
                className="multiselect-trigger"
                onClick={() => setIsMonthDropdownOpen(!isMonthDropdownOpen)}
              >
                <span>{getMonthDropdownLabel()}</span>
                <ChevronDown size={12} />
              </button>

              {isMonthDropdownOpen && (
                <div className="multiselect-menu">
                  {/* Select All Option */}
                  <div 
                    className={`multiselect-item ${selectedWeeks.length === 0 ? 'active' : ''}`}
                    onClick={selectAllMonths}
                  >
                    <div className="custom-radio-check">
                      {selectedWeeks.length === 0 && <Check size={10} strokeWidth={3} />}
                    </div>
                    <span>All Months</span>
                  </div>

                  {/* Individual Month Options */}
                  {allAvailablePeriods.map(m => {
                    const isSelected = selectedWeeks.length > 0 && selectedWeeks.includes(m);
                    return (
                      <div 
                        key={m}
                        className={`multiselect-item ${isSelected ? 'active' : ''}`}
                        onClick={() => toggleMonthSelection(m)}
                      >
                        <div className="custom-radio-check">
                          {isSelected && <Check size={10} strokeWidth={3} />}
                        </div>
                        <span>{m}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="filter-group">
            <label>Weeks:</label>
            <select 
              className="custom-select"
              value={selectedWeeks[0] || ''}
              onChange={(e) => setSelectedWeeks(e.target.value ? [e.target.value] : [])}
            >
              <option value="">All Weeks</option>
              {filters?.week_options?.map(w => (
                <option key={w} value={w}>{w}</option>
              ))}
            </select>
          </div>
        )}

        {/* Branch Slicer */}
        <div className="filter-group">
          <label>Branch:</label>
          <select 
            className="custom-select"
            value={selectedBranches[0] || ''}
            onChange={(e) => setSelectedBranches(e.target.value ? [e.target.value] : [])}
          >
            <option value="">All Branches</option>
            {filters?.branch_options?.map(b => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
        </div>

        {/* Channel Slicer (Clean single All Channels option) */}
        <div className="filter-group">
          <label>Channel:</label>
          <select 
            className="custom-select"
            value={selectedChannels[0] || ''}
            onChange={(e) => setSelectedChannels(e.target.value ? [e.target.value] : [])}
          >
            <option value="">All Channels</option>
            {filters?.channel_options?.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Dynamic Comparison KPIs in Crores */}
      <div className="kpi-grid-4">
        <div className="metric-card">
          <div className="metric-label">{mode === 'monthly' ? 'Latest Month Exposure' : 'Latest Week Exposure'}</div>
          <div className="metric-value">₹{kpis.val_end?.toFixed(2)} Cr</div>
          <div className="metric-delta">
            {mode === 'monthly' ? 'All active depots' : 'Active period stock'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">{mode === 'monthly' ? 'MoM Net Variance' : 'Net Trajectory Change'}</div>
          <div className="metric-value" style={{ color: kpis.net_4wk_change >= 0 ? '#991B1B' : '#059669' }}>
            {kpis.net_4wk_change >= 0 ? '+' : ''}₹{kpis.net_4wk_change?.toFixed(2)} Cr
          </div>
          <div className="metric-delta" style={{ color: kpis.pct_4wk_growth >= 0 ? '#991B1B' : '#059669' }}>
            {kpis.pct_4wk_growth >= 0 ? '+' : ''}{kpis.pct_4wk_growth?.toFixed(1)}% {mode === 'monthly' ? 'MoM' : 'period variance'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Primary Driver</div>
          <div className="metric-value">{kpis.driver_cat}</div>
          <div className="metric-delta" style={{ color: '#991B1B' }}>
            {kpis.driver_delta >= 0 ? '+' : ''}₹{kpis.driver_delta?.toFixed(2)} Cr impact
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Aging Index (&lt;50% life)</div>
          <div className="metric-value">{kpis.aging_idx_pct?.toFixed(1)}%</div>
          <div className="metric-delta">₹{kpis.safe_stock_cr?.toFixed(2)} Cr safe stock (&gt;70%)</div>
        </div>
      </div>

      {/* Top 3 Comparison Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, flex: 1.1, minHeight: 0, overflow: 'hidden' }}>
        
        {/* ========================================================= */}
        {/* CHART 1: Category-wise Risk Evolution across 4 Weeks     */}
        {/* ========================================================= */}
        <div className="chart-card">
          <h4>
            {isWeekly 
              ? 'Category-wise Risk Evolution across 4 Weeks (Cr)' 
              : 'Category Monthly Comparison (Cr)'}
          </h4>
          <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              {isWeekly ? (
                /* Weekly Mode: Grouped Bar Chart by Category on X-axis */
                <BarChart data={weeklyCatChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                  <XAxis dataKey="category" tick={{ fill: 'var(--text-main)', fontSize: 8 }} interval={0} />
                  <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                  <Tooltip />
                  {activePeriodsList.map((wk, i) => (
                    <Bar key={wk} dataKey={wk} fill={colors[i % colors.length]} />
                  ))}
                </BarChart>
              ) : (
                /* Monthly Mode: Monthly Trend Line Chart */
                <LineChart data={monthlyCatChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                  <XAxis dataKey="period" tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                  <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                  <Tooltip />
                  {catNames.map((c, i) => (
                    <Line key={c} type="monotone" dataKey={c} stroke={colors[i % colors.length]} strokeWidth={2} dot={{ r: 3 }} />
                  ))}
                </LineChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>

        {/* ========================================================= */}
        {/* CHART 2: 4-Week Shelf-Life Risk Distribution Migration   */}
        {/* ========================================================= */}
        <div className="chart-card">
          <h4>
            {isWeekly 
              ? '4-Week Shelf-Life Risk Distribution Migration (Cr)' 
              : 'Shelf-Life Monthly Shift (Cr)'}
          </h4>
          <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              {isWeekly ? (
                /* Weekly Mode: Stacked Bar Chart with Week on X-axis & Buckets Stacked */
                <BarChart data={weeklyBucketChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                  <XAxis dataKey="week" tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                  <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                  <Tooltip />
                  {allBucketsOrder.map((b, i) => (
                    <Bar key={b} dataKey={b} stackId="a" fill={bucketColors[i % bucketColors.length]} />
                  ))}
                </BarChart>
              ) : (
                /* Monthly Mode: Monthly Trend Line Chart */
                <LineChart data={monthlyBucketChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                  <XAxis dataKey="period" tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                  <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                  <Tooltip />
                  {bucketNames.map((b, i) => (
                    <Line key={b} type="monotone" dataKey={b} stroke={colors[i % colors.length]} strokeWidth={2} dot={{ r: 3 }} />
                  ))}
                </LineChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>

        {/* ========================================================= */}
        {/* CHART 3: Regional Branch Risk Comparison across 4 Weeks  */}
        {/* ========================================================= */}
        <div className="chart-card">
          <h4>
            {isWeekly 
              ? 'Regional Branch Risk Comparison across 4 Weeks (Cr)' 
              : 'Branch Monthly Comparison (Cr)'}
          </h4>
          <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={branchChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                <XAxis dataKey="branch" tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                <Tooltip />
                {activePeriodsList.map((w, i) => (
                  <Bar key={w} dataKey={w} fill={colors[i % colors.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom 3 Comparison Matrices */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, flex: 1.3, minHeight: 0, overflow: 'hidden' }}>
        {/* Matrix 1: Category Matrix */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
          <h3 className="section-header">{mode === 'monthly' ? 'Category Monthly Matrix (Cr)' : 'Category Evolution Matrix (Cr)'}</h3>
          <div className="table-wrapper" style={{ background: 'var(--tbl-bg)' }}>
            <table className="styled-table">
              <thead>
                <tr>
                  {matrices.cat_matrix?.columns.map(c => (
                    <th key={c} style={{ textAlign: c === 'Category' ? 'left' : 'right' }}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrices.cat_matrix?.rows.map((r, i) => {
                  const isTotal = String(r['Category'] || '').toLowerCase() === 'total';
                  return (
                    <tr key={i} className={isTotal ? 'total-row' : ''}>
                      {matrices.cat_matrix?.columns.map(c => (
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

        {/* Matrix 2: Shelf-Life Bucket Matrix */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
          <h3 className="section-header">{mode === 'monthly' ? 'Shelf-Life Monthly Matrix (Cr)' : 'Shelf-Life Health Matrix (Cr)'}</h3>
          <div className="table-wrapper" style={{ background: 'var(--tbl-bg)' }}>
            <table className="styled-table">
              <thead>
                <tr>
                  {matrices.bucket_matrix?.columns.map(c => (
                    <th key={c} style={{ textAlign: c === 'Bucket %' ? 'left' : 'right' }}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrices.bucket_matrix?.rows.map((r, i) => {
                  const isTotal = String(r['Bucket %'] || '').toLowerCase() === 'total';
                  return (
                    <tr key={i} className={isTotal ? 'total-row' : ''}>
                      {matrices.bucket_matrix?.columns.map(c => (
                        <td key={c} style={{ textAlign: c === 'Bucket %' ? 'left' : 'right' }}>
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

        {/* Matrix 3: Top 10 Escalating SKUs */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
          <h3 className="section-header">{mode === 'monthly' ? 'Top 10 Escalating SKUs (MoM)' : 'Top 10 Escalating SKUs (Cr)'}</h3>
          <div className="table-wrapper" style={{ background: 'var(--tbl-bg)' }}>
            <table className="styled-table">
              <thead>
                <tr>
                  {matrices.escalating_skus?.columns.map(c => (
                    <th key={c} style={{ textAlign: (c === '#' || c === 'SKU Description') ? 'left' : 'right' }}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrices.escalating_skus?.rows.map((r, i) => (
                  <tr key={i}>
                    {matrices.escalating_skus?.columns.map(c => (
                      <td key={c} style={{ textAlign: (c === '#' || c === 'SKU Description') ? 'left' : 'right' }}>
                        {typeof r[c] === 'number' ? r[c].toFixed(2) : r[c]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
