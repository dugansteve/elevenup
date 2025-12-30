import { useMemo, useState, useEffect } from 'react';

/**
 * SVG-based line chart showing ranking history over time
 * Supports overall, offensive, and defensive rankings
 * Lower rank is better (1 = best), so chart is inverted
 */
function RankingsHistoryChart({
  history = [],
  currentRank,
  currentOffensiveRank,
  currentDefensiveRank,
  teamName,
  width = 320,
  height = 140
}) {
  const [activeLines, setActiveLines] = useState({
    overall: true,
    offensive: true,
    defensive: true
  });

  // Track mobile view for abbreviated labels
  const [isMobile, setIsMobile] = useState(window.innerWidth < 500);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 500);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Toggle line visibility
  const toggleLine = (lineType) => {
    setActiveLines(prev => ({
      ...prev,
      [lineType]: !prev[lineType]
    }));
  };

  const padding = { top: 15, right: 20, bottom: 20, left: 40 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Check if we have valid history data
  const hasHistory = history && history.length > 0;

  // Line colors
  const lineColors = {
    overall: '#1b5e20',    // true dark green
    offensive: '#8bc34a',  // yellowish green
    defensive: '#00897b'   // greenish blue/teal
  };

  // Calculate chart data
  const chartData = useMemo(() => {
    // Return empty data if no history
    if (!hasHistory) {
      return { points: {}, paths: {}, yAxisLabels: [], minRank: 1, maxRank: 10, dates: [] };
    }

    // Sort history by date
    const sorted = [...history].sort((a, b) => new Date(a.date) - new Date(b.date));

    // Collect all ranks from all active lines
    const allRanks = [];
    sorted.forEach(d => {
      if (activeLines.overall && d.rank) allRanks.push(d.rank);
      if (activeLines.offensive && d.offensiveRank) allRanks.push(d.offensiveRank);
      if (activeLines.defensive && d.defensiveRank) allRanks.push(d.defensiveRank);
    });

    if (allRanks.length === 0) {
      return { points: {}, yAxisLabels: [], minRank: 1, maxRank: 10 };
    }

    const minRank = Math.min(...allRanks);
    const maxRank = Math.max(...allRanks);

    // Add some padding to the range
    const rankRange = Math.max(maxRank - minRank, 5);
    const paddedMin = Math.max(1, minRank - Math.ceil(rankRange * 0.1));
    const paddedMax = maxRank + Math.ceil(rankRange * 0.1);

    // Scale functions
    const xScale = (index) => (sorted.length === 1) ? chartWidth / 2 : (index / (sorted.length - 1)) * chartWidth;
    const yScale = (rank) => {
      if (rank === null || rank === undefined) return null;
      // In SVG, y=0 is top, y=chartHeight is bottom
      // We want #1 (best rank) at TOP, so lower rank → smaller y
      // normalized=0 for best rank → y=0 (top)
      // normalized=1 for worst rank → y=chartHeight (bottom)
      const normalized = (rank - paddedMin) / (paddedMax - paddedMin);
      return normalized * chartHeight;
    };

    // Generate points for each line type
    const generatePoints = (rankKey) => {
      return sorted.map((d, i) => ({
        x: xScale(i),
        y: yScale(d[rankKey]),
        rank: d[rankKey],
        date: d.date
      })).filter(p => p.y !== null);
    };

    const points = {
      overall: generatePoints('rank'),
      offensive: generatePoints('offensiveRank'),
      defensive: generatePoints('defensiveRank')
    };

    // Create SVG paths
    const createPath = (pts) => {
      if (pts.length === 0) return '';
      return pts.map((p, i) =>
        (i === 0 ? 'M' : 'L') + ` ${p.x} ${p.y}`
      ).join(' ');
    };

    // Y-axis labels
    const yAxisLabels = [];
    const step = Math.ceil((paddedMax - paddedMin) / 4);
    for (let r = paddedMin; r <= paddedMax; r += step) {
      yAxisLabels.push({
        rank: r,
        y: yScale(r)
      });
    }

    return {
      points,
      paths: {
        overall: createPath(points.overall),
        offensive: createPath(points.offensive),
        defensive: createPath(points.defensive)
      },
      yAxisLabels,
      minRank: paddedMin,
      maxRank: paddedMax,
      dates: sorted.map(d => d.date)
    };
  }, [history, chartWidth, chartHeight, activeLines, hasHistory]);

  // Format date for display
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  // Show message when no history data
  if (!hasHistory) {
    return (
      <div style={{
        padding: '1.5rem',
        background: '#f8f9fa',
        borderRadius: '8px',
        textAlign: 'center'
      }}>
        <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.75rem' }}>
          Ranking History
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '1.5rem',
          marginBottom: '0.75rem'
        }}>
          <div>
            <div style={{ fontSize: '1.75rem', fontWeight: '700', color: '#1b5e20' }}>
              #{currentRank || '-'}
            </div>
            <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase' }}>Overall</div>
          </div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#8bc34a' }}>
              #{currentOffensiveRank || '-'}
            </div>
            <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase' }}>Off</div>
          </div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#00897b' }}>
              #{currentDefensiveRank || '-'}
            </div>
            <div style={{ fontSize: '0.7rem', color: '#888', textTransform: 'uppercase' }}>Def</div>
          </div>
        </div>
        <div style={{ fontSize: '0.8rem', color: '#888' }}>
          History will appear after multiple ranking updates
        </div>
      </div>
    );
  }

  return (
    <div style={{
      background: '#fff',
      borderRadius: '8px',
      padding: '1rem',
      border: '1px solid #e0e0e0'
    }}>
      {/* Legend / Toggle buttons */}
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        marginBottom: '0.5rem',
        flexWrap: 'wrap'
      }}>
        <button
          onClick={() => toggleLine('overall')}
          style={{
            padding: '0.25rem 0.5rem',
            borderRadius: '4px',
            border: `2px solid ${lineColors.overall}`,
            background: activeLines.overall ? lineColors.overall : 'white',
            color: activeLines.overall ? 'white' : lineColors.overall,
            fontSize: '0.7rem',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem'
          }}
        >
          <span style={{
            width: '10px',
            height: '3px',
            background: activeLines.overall ? 'white' : lineColors.overall,
            borderRadius: '2px'
          }} />
          Overall #{currentRank}
        </button>
        <button
          onClick={() => toggleLine('offensive')}
          style={{
            padding: '0.25rem 0.5rem',
            borderRadius: '4px',
            border: `2px solid ${lineColors.offensive}`,
            background: activeLines.offensive ? lineColors.offensive : 'white',
            color: activeLines.offensive ? 'white' : lineColors.offensive,
            fontSize: '0.7rem',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem'
          }}
        >
          <span style={{
            width: '10px',
            height: '3px',
            background: activeLines.offensive ? 'white' : lineColors.offensive,
            borderRadius: '2px'
          }} />
          {isMobile ? 'Off' : 'Offense'} #{currentOffensiveRank || '-'}
        </button>
        <button
          onClick={() => toggleLine('defensive')}
          style={{
            padding: '0.25rem 0.5rem',
            borderRadius: '4px',
            border: `2px solid ${lineColors.defensive}`,
            background: activeLines.defensive ? lineColors.defensive : 'white',
            color: activeLines.defensive ? 'white' : lineColors.defensive,
            fontSize: '0.7rem',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem'
          }}
        >
          <span style={{
            width: '10px',
            height: '3px',
            background: activeLines.defensive ? 'white' : lineColors.defensive,
            borderRadius: '2px'
          }} />
          {isMobile ? 'Def' : 'Defense'} #{currentDefensiveRank || '-'}
        </button>
      </div>

      {/* Chart */}
      <svg
        width={width}
        height={height}
        style={{ display: 'block', maxWidth: '100%' }}
        viewBox={`0 0 ${width} ${height}`}
      >
        {/* Chart area */}
        <g transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Grid lines */}
          {chartData.yAxisLabels.map((label, i) => (
            <g key={i}>
              <line
                x1={0}
                y1={label.y}
                x2={chartWidth}
                y2={label.y}
                stroke="#eee"
                strokeWidth={1}
              />
              <text
                x={-8}
                y={label.y}
                textAnchor="end"
                alignmentBaseline="middle"
                fill="#888"
                fontSize="10"
              >
                #{label.rank}
              </text>
            </g>
          ))}

          {/* Lines for each ranking type */}
          {activeLines.overall && chartData.paths?.overall && (
            <path
              d={chartData.paths.overall}
              fill="none"
              stroke={lineColors.overall}
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
          {activeLines.offensive && chartData.paths?.offensive && (
            <path
              d={chartData.paths.offensive}
              fill="none"
              stroke={lineColors.offensive}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="5,3"
            />
          )}
          {activeLines.defensive && chartData.paths?.defensive && (
            <path
              d={chartData.paths.defensive}
              fill="none"
              stroke={lineColors.defensive}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="2,2"
            />
          )}

          {/* Data points for all ranking types */}
          {activeLines.overall && chartData.points?.overall?.map((point, i) => (
            <circle
              key={`overall-${i}`}
              cx={point.x}
              cy={point.y}
              r={4}
              fill="white"
              stroke={lineColors.overall}
              strokeWidth={2}
            />
          ))}
          {activeLines.offensive && chartData.points?.offensive?.map((point, i) => (
            <circle
              key={`offensive-${i}`}
              cx={point.x}
              cy={point.y}
              r={3.5}
              fill="white"
              stroke={lineColors.offensive}
              strokeWidth={2}
            />
          ))}
          {activeLines.defensive && chartData.points?.defensive?.map((point, i) => (
            <circle
              key={`defensive-${i}`}
              cx={point.x}
              cy={point.y}
              r={3.5}
              fill="white"
              stroke={lineColors.defensive}
              strokeWidth={2}
            />
          ))}

          {/* X-axis date labels */}
          {chartData.dates && chartData.dates.length > 0 && (
            <>
              {/* First date */}
              <text
                x={chartData.points?.overall?.[0]?.x || 0}
                y={chartHeight + 15}
                textAnchor="start"
                fill="#888"
                fontSize="9"
              >
                {formatDate(chartData.dates[0])}
              </text>
              {/* Last date */}
              {chartData.dates.length > 1 && (
                <text
                  x={chartData.points?.overall?.[chartData.dates.length - 1]?.x || chartWidth}
                  y={chartHeight + 15}
                  textAnchor="end"
                  fill="#888"
                  fontSize="9"
                >
                  {formatDate(chartData.dates[chartData.dates.length - 1])}
                </text>
              )}
            </>
          )}
        </g>
      </svg>
    </div>
  );
}

export default RankingsHistoryChart;
