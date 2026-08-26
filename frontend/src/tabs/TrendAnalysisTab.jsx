import React, { useState, useEffect } from 'react';
import { getTrendData } from '../api';
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ComposedChart
} from 'recharts';

export default function TrendAnalysisTab() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  
  const [dimension, setDimension] = useState('Category');
  const [metric, setMetric] = useState('At-Risk Value (Cr)');
  const [topN, setTopN] = useState(10);
  const [selectedBranches, setSelectedBranches] = useState([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getTrendData({
        dimension,
        metric,
        top_n: topN,
        branches: selectedBranches
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
  }, [dimension, metric, topN, selectedBranches]);

  if (loading && !data) {
    return <div style={{ padding: 20, textAlign: 'center', color: '#6B21A8', fontSize: 13 }}>Loading Trend Analytics...</div>;
  }

  if (!data) {
    return <div style={{ padding: 20, fontSize: 13 }}>No trend data available.</div>;
  }

  const { filters, kpis, charts, leaderboard } = data;

  // Chart 1: Trajectory Trend (Top items over active weeks)
  const trajectoryDataMap = {};
  const itemNamesSet = new Set();
  charts?.trajectory?.forEach(d => {
    if (!trajectoryDataMap[d.week]) trajectoryDataMap[d.week] = { week: d.week };
    const numVal = d.value ?? d.val ?? d.value_cr ?? 0;
    trajectoryDataMap[d.week][d.item] = numVal;
    itemNamesSet.add(d.item);
  });
  const trajectoryChartData = Object.values(trajectoryDataMap);
  const trajectoryItems = Array.from(itemNamesSet);

  // Chart 2: Pareto Distribution
  const paretoChartData = (charts?.pareto || []).map(p => ({
    item: p.item,
    value_cr: p.value_cr ?? p.val ?? 0,
    cum_pct: p.cum_pct ?? p.cumulative_pct ?? 0
  }));

  // Chart 3: Health Profile (All 8 buckets: 20 TO 30 to 80 to 85)
  const compDataMap = {};
  const healthProfileBuckets = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75', '75 to 80', '80 to 85'];
  charts?.shelf_life_comp?.forEach(d => {
    if (!compDataMap[d.item]) compDataMap[d.item] = { item: d.item };
    const numVal = d.value_cr ?? d.val ?? d.value ?? 0;
    compDataMap[d.item][d.bucket] = numVal;
  });
  const compChartData = Object.values(compDataMap);

  // Chart 4: Regional Branch Breakdown
  const branchDataMap = {};
  const activeBranches = ['01.North', '02.East', '03.West', '04.South'];
  charts?.branch_breakdown?.forEach(d => {
    if (!branchDataMap[d.item]) branchDataMap[d.item] = { item: d.item };
    const numVal = d.value_cr ?? d.val ?? d.value ?? 0;
    branchDataMap[d.item][d.branch] = numVal;
  });
  const branchChartData = Object.values(branchDataMap);

  const colors = ['#7C3AED', '#EC4899', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#14B8A6'];
  const healthColors = ['#EF4444', '#F97316', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#6366F1'];
  const branchColors = ['#7C3AED', '#3B82F6', '#10B981', '#F59E0B'];

  return (
    <div className="tab-view-container">
      {/* Slicers Bar */}
      <div className="filter-bar">
        <div className="filter-group">
          <label>Dimension:</label>
          <select 
            className="custom-select"
            value={dimension}
            onChange={(e) => setDimension(e.target.value)}
          >
            <option value="Category">Category</option>
            <option value="Brand (IOP)">Brand</option>
            <option value="Product / SKU">Product / SKU</option>
            <option value="Branch">Branch</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Metric:</label>
          <select 
            className="custom-select"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          >
            <option value="At-Risk Value (Cr)">At-Risk Value (Cr)</option>
            <option value="Total Stock (Cases)">Total Stock (Cases)</option>
            <option value="High Risk % (20-50%)">High Risk % (20-50%)</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Top Items:</label>
          <select 
            className="custom-select"
            value={topN}
            onChange={(e) => setTopN(e.target.value === 'All' ? 'All' : parseInt(e.target.value))}
          >
            <option value={5}>Top 5</option>
            <option value={10}>Top 10</option>
            <option value={15}>Top 15</option>
            <option value="All">All</option>
          </select>
        </div>

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
      </div>

      {/* 4 KPI Metric Cards in Crores */}
      <div className="kpi-grid-4">
        <div className="metric-card">
          <div className="metric-label">Leading {dimension}</div>
          <div className="metric-value">{kpis.top_contributor_name || 'N/A'}</div>
          <div className="metric-delta">
            ₹{kpis.top_contributor_val?.toFixed(2)} Cr ({kpis.top_contributor_pct?.toFixed(1)}% share)
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Pareto 80/20 Driver Count</div>
          <div className="metric-value">{kpis.pareto_count} {dimension}s</div>
          <div className="metric-delta">
            {kpis.pareto_pct?.toFixed(1)}% of items drive 80% volume
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Freshness Ratio (&gt;70% Life)</div>
          <div className="metric-value" style={{ color: '#059669' }}>
            {kpis.freshness_ratio?.toFixed(1)}%
          </div>
          <div className="metric-delta">Safe inventory profile</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">High Risk Exposure (20-50%)</div>
          <div className="metric-value" style={{ color: '#991B1B' }}>
            ₹{kpis.high_risk_val?.toFixed(2)} Cr
          </div>
          <div className="metric-delta">{kpis.high_risk_pct?.toFixed(1)}% of total stock</div>
        </div>
      </div>

      {/* Top 4 Visualizations Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, flex: 1.1, minHeight: 0, overflow: 'hidden' }}>
        
        {/* Chart 1: Trajectory Trend */}
        <div className="chart-card">
          <h4>{dimension} Trajectory ({metric.includes('Cases') ? 'Cases' : 'Cr'})</h4>
          <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trajectoryChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                <XAxis dataKey="week" tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                <Tooltip />
                {trajectoryItems.map((item, i) => (
                  <Line key={item} type="monotone" dataKey={item} stroke={colors[i % colors.length]} strokeWidth={2} dot={{ r: 2 }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Pareto Distribution */}
        <div className="chart-card">
          <h4>Pareto Analysis (Cr vs %)</h4>
          <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={paretoChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                <XAxis dataKey="item" tick={{ fill: 'var(--text-main)', fontSize: 8 }} interval={0} />
                <YAxis yAxisId="left" tick={{ fill: 'var(--text-main)', fontSize: 8 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: 'var(--text-main)', fontSize: 8 }} domain={[0, 100]} />
                <Tooltip />
                <Bar yAxisId="left" dataKey="value_cr" fill="#7C3AED" />
                <Line yAxisId="right" type="monotone" dataKey="cum_pct" stroke="#EC4899" strokeWidth={2} dot={{ r: 2 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: Shelf-Life Health Profile (20 TO 30 to 80 to 85) */}
        <div className="chart-card">
          <h4>Health Profile (20-30% to 80-85%)</h4>
          <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={compChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                <XAxis dataKey="item" tick={{ fill: 'var(--text-main)', fontSize: 8 }} interval={0} />
                <YAxis tick={{ fill: 'var(--text-main)', fontSize: 8 }} />
                <Tooltip />
                {healthProfileBuckets.map((b, i) => (
                  <Bar key={b} dataKey={b} stackId="a" fill={healthColors[i % healthColors.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Branch Breakdown (North, East, West, South) */}
        <div className="chart-card">
          <h4>Branch Breakdown (North, East, West, South)</h4>
          <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={branchChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                <XAxis dataKey="item" tick={{ fill: 'var(--text-main)', fontSize: 8 }} interval={0} />
                <YAxis tick={{ fill: 'var(--text-main)', fontSize: 8 }} />
                <Tooltip />
                {activeBranches.map((br, i) => (
                  <Bar key={br} dataKey={br} fill={branchColors[i % branchColors.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Strategic Leaderboard Table */}
      <div style={{ flex: 1.2, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <h3 className="section-header">{dimension} Strategic Risk Leaderboard (Cr)</h3>
        <div className="table-wrapper" style={{ background: 'var(--tbl-bg)' }}>
          <table className="styled-table">
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Rank</th>
                <th style={{ textAlign: 'left' }}>{dimension}</th>
                <th style={{ textAlign: 'right' }}>Total Exposure (Cr)</th>
                <th style={{ textAlign: 'right' }}>High Risk Val (Cr)</th>
                <th style={{ textAlign: 'right' }}>Stock (Cases)</th>
                <th style={{ textAlign: 'right' }}>High Risk %</th>
                <th style={{ textAlign: 'right' }}>Share %</th>
                <th style={{ textAlign: 'left' }}>Prescribed Strategy</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard?.map((r, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 700, textAlign: 'left' }}>{r.rank}</td>
                  <td style={{ fontWeight: 600, textAlign: 'left' }}>{r.item}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>₹{r.total_exposure_cr?.toFixed(2)} Cr</td>
                  <td style={{ textAlign: 'right', color: '#991B1B' }}>₹{r.high_risk_cr?.toFixed(2)} Cr</td>
                  <td style={{ textAlign: 'right' }}>{r.stock_cases?.toLocaleString()}</td>
                  <td style={{ textAlign: 'right' }}>{r.high_risk_pct}</td>
                  <td style={{ textAlign: 'right' }}>{r.share_pct}</td>
                  <td style={{ textAlign: 'left', fontWeight: 600, color: 'var(--text-main)' }}>{r.prescribed_strategy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
