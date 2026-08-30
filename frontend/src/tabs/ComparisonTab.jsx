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

  // Helper to format values as rounded to 1 decimal place with Indian locale commas
  const formatVal = (val) => {
    if (val === null || val === undefined || val === '') return '-';
    if (typeof val === 'number') {
      return Number(val.toFixed(1)).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    }
    const num = parseFloat(val);
    if (!isNaN(num) && typeof val === 'string' && /^-?\d+(\.\d+)?$/.test(val.trim())) {
      return Number(num.toFixed(1)).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    }
    return val;
  };

  // =========================================================================
  // DATA MAPPINGS FOR CHARTS (GROUPED & STACKED BAR CHARTS FOR ALL MODES)
  // =========================================================================

  // 1. Chart 1: Category on X-axis, Grouped Bars for each Period (Week / Month / Year)
  const catChartMap = {};
  charts?.cat_evolution?.forEach(item => {
    if (!catChartMap[item.category]) catChartMap[item.category] = { category: item.category };
    catChartMap[item.category][item.week] = item.value_cr;
  });
  const catChartData = Object.values(catChartMap);

  // 2. Chart 2: Period on X-axis, Stacked Bars by Shelf-Life Risk Bucket
  const allBucketsOrder = ['20 TO 30', '30 TO 40', '40 TO 50', '50 TO 60', '60 TO 70', '70 TO 75'];
  const bucketChartMap = {};
  charts?.bucket_migration?.forEach(item => {
    if (!bucketChartMap[item.week]) bucketChartMap[item.week] = { period: item.week };
    bucketChartMap[item.week][item.bucket] = item.value_cr;
  });
  const bucketChartData = Object.values(bucketChartMap);

  // 3. Chart 3: Branch on X-axis, Grouped Bars for each Period
  const branchDataMap = {};
  charts?.branch_comparison?.forEach(item => {
    if (!branchDataMap[item.branch]) branchDataMap[item.branch] = { branch: item.branch };
    branchDataMap[item.branch][item.week] = item.value_cr;
  });
  const branchChartData = Object.values(branchDataMap);

  const colors = ['#7C3AED', '#EC4899', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#14B8A6'];
  const bucketColors = ['#DC2626', '#EA580C', '#D97706', '#10B981', '#2563EB', '#7C3AED'];

  // Render dynamic comparison matrix table with badge and color formatting
  const renderMatrixTable = (title, matrixData, defaultLeftCol = 'CATEGORY') => {
    if (!matrixData || !matrixData.columns || matrixData.columns.length === 0) return null;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
        <h3 className="section-header">{title}</h3>
        <div className="table-wrapper" style={{ background: 'var(--tbl-bg)' }}>
          <table className="styled-table">
            <thead>
              <tr>
                {matrixData.columns.map(c => {
                  const cUp = c.toUpperCase();
                  const isLeft = c === defaultLeftCol || c === '#' || cUp.includes('CATEGORY') || cUp.includes('SKU') || cUp.includes('BUCKET') || cUp.includes('STATUS') || cUp.includes('ACTION') || cUp.includes('FLAG') || cUp.includes('MANDATE');
                  return (
                    <th key={c} style={{ textAlign: isLeft ? 'left' : 'right' }}>
                      {c}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {matrixData.rows.map((r, i) => {
                const isTotal = String(r[defaultLeftCol] || r['CATEGORY'] || r['Category'] || r['SHELF-LIFE BUCKET'] || r['Shelf-Life Bucket'] || '').toLowerCase() === 'total';
                return (
                  <tr key={i} className={isTotal ? 'total-row' : ''}>
                    {matrixData.columns.map(c => {
                      const cUp = c.toUpperCase();
                      const isLeft = c === defaultLeftCol || c === '#' || cUp.includes('CATEGORY') || cUp.includes('SKU') || cUp.includes('BUCKET') || cUp.includes('STATUS') || cUp.includes('ACTION') || cUp.includes('FLAG') || cUp.includes('MANDATE');
                      const isFlagOrStatus = cUp.includes('FLAG') || cUp === 'STATUS';
                      const isAction = cUp.includes('ACTION') || cUp.includes('MANDATE');
                      const isChangeCol = cUp.includes('NET CHANGE') || cUp.includes('W2 – W1') || cUp.includes('W3 – W2') || cUp.includes('W4 – W3') || cUp.includes('W4 - W1') || cUp.includes('W4 – W1');
                      const isVelocityOrAccum = cUp.includes('VELOCITY') || cUp.includes('ACCUMULATION') || cUp.includes('SURPLUS') || cUp.includes('RISK CHANGE');
                      const isRemainingLife = cUp.includes('REMAINING LIFE');
                      const isTrend = cUp.includes('TREND');
                      const val = r[c];

                      let cellContent;
                      let cellStyle = { textAlign: isLeft ? 'left' : 'right' };

                      if (isFlagOrStatus) {
                        const strVal = String(val || '');
                        const isRed = strVal.includes('🔴') || strVal.includes('ACTION NEEDED');
                        const isYellow = strVal.includes('🟡') || strVal.includes('Monitor') || strVal.includes('🟠');
                        cellContent = (
                          <span style={{
                            display: 'inline-block',
                            padding: '2px 7px',
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 700,
                            backgroundColor: isRed ? 'rgba(239, 68, 68, 0.14)' : (isYellow ? 'rgba(245, 158, 11, 0.14)' : 'rgba(16, 185, 129, 0.14)'),
                            color: isRed ? '#DC2626' : (isYellow ? '#D97706' : '#059669')
                          }}>
                            {val}
                          </span>
                        );
                      } else if (isAction) {
                        const strVal = String(val || '');
                        const isEmerg = strVal.includes('🚛') || strVal.includes('EMERGENCY') || strVal.includes('⚡') || strVal.includes('Priority');
                        const isDispatch = strVal.includes('📦') || strVal.includes('Immediate') || strVal.includes('SOURCE');
                        const isHold = strVal.includes('HOLD');
                        cellContent = (
                          <span style={{
                            display: 'inline-block',
                            padding: '2px 6px',
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 600,
                            backgroundColor: isEmerg ? 'rgba(239, 68, 68, 0.12)' : (isDispatch ? 'rgba(124, 58, 237, 0.12)' : (isHold ? 'rgba(245, 158, 11, 0.12)' : 'rgba(16, 185, 129, 0.12)')),
                            color: isEmerg ? '#DC2626' : (isDispatch ? '#7C3AED' : (isHold ? '#D97706' : '#059669'))
                          }}>
                            {val}
                          </span>
                        );
                      } else if (isRemainingLife) {
                        const strVal = String(val || '');
                        const isCritical = strVal.includes('Critical') || strVal.includes('<30');
                        const isRisky = strVal.includes('Risky') || strVal.includes('40-50');
                        const isBorder = strVal.includes('Borderline');
                        cellContent = (
                          <span style={{
                            display: 'inline-block',
                            padding: '2px 6px',
                            borderRadius: 4,
                            fontSize: 10,
                            fontWeight: 700,
                            backgroundColor: isCritical ? 'rgba(239, 68, 68, 0.12)' : (isRisky ? 'rgba(245, 158, 11, 0.12)' : (isBorder ? 'rgba(59, 130, 246, 0.12)' : 'rgba(16, 185, 129, 0.12)')),
                            color: isCritical ? '#DC2626' : (isRisky ? '#D97706' : (isBorder ? '#2563EB' : '#059669'))
                          }}>
                            {val}
                          </span>
                        );
                      } else if (isChangeCol) {
                        if (typeof val === 'number') {
                          const num = Number(val.toFixed(1));
                          const isPos = num > 0;
                          const isNeg = num < 0;
                          cellStyle.color = isPos ? '#DC2626' : (isNeg ? '#059669' : 'inherit');
                          cellStyle.fontWeight = 700;
                          cellContent = `${isPos ? '+' : ''}${num.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`;
                        } else {
                          const strVal = String(val || '').trim();
                          const isPos = strVal.startsWith('+');
                          const isNeg = strVal.startsWith('-');
                          cellStyle.color = isPos ? '#DC2626' : (isNeg ? '#059669' : 'inherit');
                          cellStyle.fontWeight = 700;
                          cellContent = val;
                        }
                      } else if (isVelocityOrAccum) {
                        const strVal = String(val || '');
                        const isUp = strVal.startsWith('+') || strVal.includes('Increasing') || strVal.includes('Accumulating');
                        const isDown = strVal.startsWith('-') || strVal.includes('Clearing') || strVal.includes('Decreasing');
                        cellStyle.color = isUp ? '#DC2626' : (isDown ? '#059669' : 'inherit');
                        cellStyle.fontWeight = 700;
                        cellContent = val;
                      } else if (isTrend) {
                        const strVal = String(val || '');
                        const isIncreasing = strVal.includes('Increasing') || strVal.includes('📈');
                        const isDecreasing = strVal.includes('Decreasing') || strVal.includes('📉');
                        cellContent = (
                          <span style={{
                            fontWeight: 700,
                            color: isIncreasing ? '#DC2626' : (isDecreasing ? '#059669' : 'inherit')
                          }}>
                            {val}
                          </span>
                        );
                      } else if (typeof val === 'number') {
                        cellContent = formatVal(val);
                      } else {
                        cellContent = formatVal(val);
                      }

                      return (
                        <td key={c} style={cellStyle}>
                          {cellContent}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // Render SKU Shelf-Life Breakdown Matrix (Matching Excel reference table from user image)
  const renderSkuShelfLifeTable = (title, skuData, isCompact = false) => {
    if (!skuData || !skuData.columns || skuData.columns.length === 0) return null;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden', height: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <h3 className="section-header" style={{ margin: 0 }}>{title}</h3>
          <span style={{
            fontSize: 10,
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: 4,
            background: 'rgba(245, 158, 11, 0.18)',
            color: '#D97706',
            border: '1px solid rgba(245, 158, 11, 0.3)'
          }}>
            Stock in Cr
          </span>
        </div>
        <div className="table-wrapper" style={{ background: 'var(--tbl-bg)', flex: 1, overflow: 'auto' }}>
          <table className="styled-table" style={{ fontSize: isCompact ? '10px' : '11.5px' }}>
            <thead>
              <tr>
                {skuData.columns.map(c => {
                  const isLeft = c === 'Brand' || c === 'Link Description';
                  return (
                    <th key={c} style={{
                      textAlign: isLeft ? 'left' : 'right',
                      fontWeight: 700,
                      padding: isCompact ? '4px 6px' : '6px 8px',
                      whiteSpace: 'nowrap'
                    }}>
                      {c}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {skuData.rows.map((r, i) => {
                const isTotal = String(r['Brand'] || '').toLowerCase() === 'total';
                return (
                  <tr key={i} className={isTotal ? 'total-row' : ''} style={isTotal ? { background: 'rgba(254, 226, 226, 0.45)', fontWeight: 800 } : {}}>
                    {skuData.columns.map(c => {
                      const isLeft = c === 'Brand' || c === 'Link Description';
                      const val = r[c];
                      const isDangerBucket = c === '<30%' || c === '30-40%' || c === '40-50%';
                      const isMedBucket = c === '50-60%' || c === '60-70%';
                      const isHighLifeBucket = c === '70-75%' || c === '75-80%';
                      const isTotalCol = c === 'Total';

                      let cellStyle = {
                        textAlign: isLeft ? 'left' : 'right',
                        padding: isCompact ? '3px 5px' : '5px 8px',
                        whiteSpace: isLeft ? 'normal' : 'nowrap'
                      };

                      let cellContent = val;

                      if (typeof val === 'number') {
                        const num = Number(val.toFixed(1));
                        cellContent = num === 0 ? '0' : num.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
                        
                        if (!isTotal) {
                          if (num > 0 && isDangerBucket) {
                            cellStyle.backgroundColor = 'rgba(239, 68, 68, 0.10)';
                            cellStyle.color = '#DC2626';
                            cellStyle.fontWeight = 700;
                          } else if (num > 0 && isMedBucket) {
                            cellStyle.backgroundColor = 'rgba(124, 58, 237, 0.08)';
                            cellStyle.color = '#7C3AED';
                          } else if (num > 0 && isHighLifeBucket) {
                            cellStyle.backgroundColor = 'rgba(245, 158, 11, 0.08)';
                            cellStyle.color = '#D97706';
                          } else if (isTotalCol) {
                            cellStyle.fontWeight = 700;
                          }
                        }
                      } else if (isLeft && isTotal) {
                        cellStyle.fontWeight = 800;
                      }

                      return (
                        <td key={c} style={cellStyle}>
                          {cellContent}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

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

      {/* Dynamic Period Executive Overview Cards (High Risk Values & WoW / MoM Deltas) */}
      <div 
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${Math.max(1, Math.min(kpis.executive_cards?.length || 4, 4))}, 1fr)`,
          gap: 6,
          flexShrink: 0,
          minHeight: 54,
          height: 54
        }}
      >
        {kpis.executive_cards && kpis.executive_cards.length > 0 ? (
          kpis.executive_cards.slice(0, 4).map((card, idx) => {
            const isPositive = card.delta_cr > 0;
            const isNegative = card.delta_cr < 0;
            const deltaColor = card.is_baseline 
              ? 'var(--metric-label-color)' 
              : (isPositive ? '#DC2626' : (isNegative ? '#059669' : 'var(--metric-label-color)'));

            return (
              <div key={card.period || idx} className="metric-card">
                <div className="metric-label">{card.title}</div>
                <div className="metric-value">₹{Number(card.value_cr || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr</div>
                <div className="metric-delta" style={{ color: deltaColor, fontWeight: 700 }}>
                  {card.delta_str}
                </div>
              </div>
            );
          })
        ) : (
          /* Fallback if no executive cards */
          <>
            <div className="metric-card">
              <div className="metric-label">{mode === 'monthly' ? 'Latest Month Exposure' : (mode === 'yearly' ? 'Latest Year Exposure' : 'Latest Week Exposure')}</div>
              <div className="metric-value">₹{Number(kpis.val_end || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr</div>
              <div className="metric-delta">{mode === 'monthly' ? 'All active depots' : 'Active period stock'}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">{mode === 'monthly' ? 'MoM Net Variance' : (mode === 'yearly' ? 'YoY Net Variance' : 'Net Trajectory Change')}</div>
              <div className="metric-value" style={{ color: kpis.net_4wk_change >= 0 ? '#991B1B' : '#059669' }}>
                {kpis.net_4wk_change >= 0 ? '+' : ''}₹{Number(kpis.net_4wk_change || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr
              </div>
              <div className="metric-delta" style={{ color: kpis.pct_4wk_growth >= 0 ? '#991B1B' : '#059669' }}>
                {kpis.pct_4wk_growth >= 0 ? '+' : ''}{kpis.pct_4wk_growth?.toFixed(1)}% {mode === 'monthly' ? 'MoM' : (mode === 'yearly' ? 'YoY' : 'variance')}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Primary Driver</div>
              <div className="metric-value">{kpis.driver_cat}</div>
              <div className="metric-delta" style={{ color: '#991B1B' }}>
                {kpis.driver_delta >= 0 ? '+' : ''}₹{Number(kpis.driver_delta || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr impact
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Aging Index (&lt;50% life)</div>
              <div className="metric-value">{kpis.aging_idx_pct?.toFixed(1)}%</div>
              <div className="metric-delta">₹{Number(kpis.safe_stock_cr || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr safe stock (&gt;70%)</div>
            </div>
          </>
        )}
      </div>

      {mode === 'yearly' && data?.is_complete_year === false ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          flex: 1,
          background: 'var(--tbl-bg)',
          borderRadius: 8,
          border: '1px dashed var(--tbl-border)',
          padding: '40px 24px',
          textAlign: 'center',
          margin: '10px 0'
        }}>
          <div style={{ fontSize: 38, marginBottom: 12 }}>📅</div>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-main)', marginBottom: 8 }}>
            12 Months Required for Yearly Comparison
          </h3>
          <p style={{ fontSize: 13, color: 'var(--metric-label-color)', maxWidth: 540, lineHeight: 1.5, marginBottom: 16 }}>
            Yearly comparison requires complete 12-month data (January – December). Currently, only <strong>{data?.available_months_count || data?.filters?.week_options?.length || 0} / 12 months</strong> are available.
          </p>
          <div style={{
            padding: '9px 18px',
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            borderRadius: 6,
            color: '#DC2626',
            fontWeight: 600,
            fontSize: 13
          }}>
            ⚠️ Please add respective 12 months data to enable Yearly Comparison
          </div>
        </div>
      ) : (
        <>
          {/* Comparison Content */}
          {isWeekly ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1, minHeight: 0, overflow: 'hidden' }}>
              {/* Weekly Top Row: 4 Columns (3 Charts + 1 SKU Shelf-Life Table) */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1.35fr', gap: 6, flex: 1.15, minHeight: 0, overflow: 'hidden' }}>
                {/* CHART 1: Weekly Category Grouped Bar Chart */}
                <div className="chart-card">
                  <h4>Category-wise Risk Evolution across Weeks (Cr)</h4>
                  <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={catChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                        <XAxis dataKey="category" tick={{ fill: 'var(--text-main)', fontSize: 8 }} interval={0} />
                        <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <Tooltip formatter={(val, name) => [`₹${Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr`, name]} />
                        {activePeriodsList.map((period, i) => (
                          <Bar key={period} dataKey={period} fill={colors[i % colors.length]} />
                        ))}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* CHART 2: Weekly Shelf-Life Stacked Bar Chart */}
                <div className="chart-card">
                  <h4>Shelf-Life Risk Migration across Weeks (Cr)</h4>
                  <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={bucketChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                        <XAxis dataKey="period" tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <Tooltip formatter={(val, name) => [`₹${Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr`, name]} />
                        {allBucketsOrder.map((b, i) => (
                          <Bar key={b} dataKey={b} stackId="a" fill={bucketColors[i % bucketColors.length]} />
                        ))}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* CHART 3: Weekly Branch Grouped Bar Chart */}
                <div className="chart-card">
                  <h4>Regional Branch Risk Comparison across Weeks (Cr)</h4>
                  <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={branchChartData} margin={{ top: 2, right: 4, left: -22, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                        <XAxis dataKey="branch" tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <Tooltip formatter={(val, name) => [`₹${Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr`, name]} />
                        {activePeriodsList.map((w, i) => (
                          <Bar key={w} dataKey={w} fill={colors[i % colors.length]} />
                        ))}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* COLUMN 4: SKU Shelf-Life Breakdown Matrix (Matching Image) */}
                <div className="chart-card" style={{ padding: '6px 8px', display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
                  {renderSkuShelfLifeTable('Brand & SKU Shelf-Life Matrix', matrices.sku_matrix, true)}
                </div>
              </div>

              {/* Bottom Matrices Grid: 4-table Grid for Weekly Dashboard */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6, flex: 1.25, minHeight: 0, overflow: 'auto' }}>
                {renderMatrixTable('Table 1: Category-wise Weekly Stock Trend', matrices.cat_matrix, 'CATEGORY')}
                {renderMatrixTable('Table 2: Shelf-Life Bucket-wise Weekly Stock Position', matrices.bucket_matrix, 'SHELF-LIFE BUCKET')}
                {renderMatrixTable('Table 3: Top Brands by Surplus Accumulation (W4 vs W1)', matrices.top_brands || matrices.sku_watchlist, 'BRAND')}
                {renderMatrixTable('Table 4: Category-wise Week-over-Week Movement Delta', matrices.wow_movement || matrices.inter_depot_movement, 'CATEGORY')}
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1, minHeight: 0, overflow: 'auto' }}>
              {/* Monthly Top 3 Charts */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, minHeight: 180, height: 195, flexShrink: 0 }}>
                {/* MONTHLY CHART 1: Red-Zone Shelf-Life Trajectory (20% to 50%) */}
                <div className="chart-card">
                  <h4>Red-Zone Shelf-Life Trajectory (20% to 50%)</h4>
                  <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={charts.red_zone_trajectory || []} margin={{ top: 6, right: 12, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                        <XAxis dataKey="month" tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <Tooltip formatter={(val, name) => [`₹${Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr`, name]} />
                        <Line type="monotone" dataKey="Total Red-Zone" stroke="#DC2626" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                        <Line type="monotone" dataKey="20 TO 30" stroke="#EF4444" strokeWidth={2} strokeDasharray="3 3" dot={{ r: 3 }} />
                        <Line type="monotone" dataKey="30 TO 40" stroke="#EA580C" strokeWidth={2} strokeDasharray="3 3" dot={{ r: 3 }} />
                        <Line type="monotone" dataKey="40 TO 50" stroke="#D97706" strokeWidth={2} strokeDasharray="3 3" dot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* MONTHLY CHART 2: Category-wise Stock: Baseline vs. Current Month */}
                <div className="chart-card">
                  <h4>Category-wise Stock: Baseline vs. Current Month</h4>
                  <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={charts.cat_baseline_vs_current || []} margin={{ top: 6, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                        <XAxis dataKey="category" tick={{ fill: 'var(--text-main)', fontSize: 8 }} interval={0} />
                        <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <Tooltip formatter={(val, name) => [`₹${Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr`, name]} />
                        {charts.cat_baseline_vs_current && charts.cat_baseline_vs_current.length > 0 && (
                          <>
                            {Object.keys(charts.cat_baseline_vs_current[0] || {})
                              .filter(k => k.includes('(Baseline)'))
                              .map(k => (
                                <Bar key={k} dataKey={k} fill="#3B82F6" />
                              ))}
                            {Object.keys(charts.cat_baseline_vs_current[0] || {})
                              .filter(k => k.includes('(Current)'))
                              .map(k => (
                                <Bar key={k} dataKey={k} fill="#7C3AED" />
                              ))}
                          </>
                        )}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* MONTHLY CHART 3: Monthly Liquidation Velocity */}
                <div className="chart-card">
                  <h4>Monthly Liquidation Velocity (Stock Cleared MoM)</h4>
                  <div style={{ flex: 1, minHeight: 0, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={charts.liquidation_velocity || []} margin={{ top: 6, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid-stroke)" />
                        <XAxis dataKey="period" tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <YAxis tick={{ fill: 'var(--text-main)', fontSize: 9 }} />
                        <Tooltip formatter={(val, name) => [`₹${Number(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr`, name]} />
                        <Bar dataKey="cleared_cr" name="Cleared Stock (Cr)" fill="#10B981" />
                        <Bar dataKey="accumulated_cr" name="Accumulated Stock (Cr)" fill="#DC2626" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Monthly Middle 3 Tables */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, minHeight: 200, height: 215, flexShrink: 0 }}>
                {renderMatrixTable('Table 1: Category-wise Month-End Stock Trend', matrices.cat_matrix, 'CATEGORY')}
                {renderMatrixTable('Table 2: Shelf-Life Risk Concentration Trend', matrices.bucket_matrix, 'SHELF-LIFE BUCKET')}
                {renderMatrixTable('Table 3: Top Brands – Cumulative Surplus Trend', matrices.brand_surplus_matrix || matrices.escalating_skus, 'BRAND')}
              </div>

              {/* Monthly Bottom Table 4: Brand & SKU Shelf-Life Distribution Matrix (Matching Image) */}
              <div style={{ minHeight: 220, height: 240, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
                {renderSkuShelfLifeTable('Table 4: Brand & SKU Shelf-Life Distribution Matrix (Stock in Cr)', matrices.sku_matrix, false)}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}