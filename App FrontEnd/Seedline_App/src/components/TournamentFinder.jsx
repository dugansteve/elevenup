import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import SuggestTournament from './SuggestTournament';
import TournamentMap from './TournamentMap';
import BottomSheetSelect from './BottomSheetSelect';

// US States for dropdown
const US_STATES = [
  { code: 'ALL', name: 'All States' },
  { code: 'AL', name: 'Alabama' },
  { code: 'AK', name: 'Alaska' },
  { code: 'AZ', name: 'Arizona' },
  { code: 'AR', name: 'Arkansas' },
  { code: 'CA', name: 'California' },
  { code: 'CO', name: 'Colorado' },
  { code: 'CT', name: 'Connecticut' },
  { code: 'DE', name: 'Delaware' },
  { code: 'FL', name: 'Florida' },
  { code: 'GA', name: 'Georgia' },
  { code: 'HI', name: 'Hawaii' },
  { code: 'ID', name: 'Idaho' },
  { code: 'IL', name: 'Illinois' },
  { code: 'IN', name: 'Indiana' },
  { code: 'IA', name: 'Iowa' },
  { code: 'KS', name: 'Kansas' },
  { code: 'KY', name: 'Kentucky' },
  { code: 'LA', name: 'Louisiana' },
  { code: 'ME', name: 'Maine' },
  { code: 'MD', name: 'Maryland' },
  { code: 'MA', name: 'Massachusetts' },
  { code: 'MI', name: 'Michigan' },
  { code: 'MN', name: 'Minnesota' },
  { code: 'MS', name: 'Mississippi' },
  { code: 'MO', name: 'Missouri' },
  { code: 'MT', name: 'Montana' },
  { code: 'NE', name: 'Nebraska' },
  { code: 'NV', name: 'Nevada' },
  { code: 'NH', name: 'New Hampshire' },
  { code: 'NJ', name: 'New Jersey' },
  { code: 'NM', name: 'New Mexico' },
  { code: 'NY', name: 'New York' },
  { code: 'NC', name: 'North Carolina' },
  { code: 'ND', name: 'North Dakota' },
  { code: 'OH', name: 'Ohio' },
  { code: 'OK', name: 'Oklahoma' },
  { code: 'OR', name: 'Oregon' },
  { code: 'PA', name: 'Pennsylvania' },
  { code: 'RI', name: 'Rhode Island' },
  { code: 'SC', name: 'South Carolina' },
  { code: 'SD', name: 'South Dakota' },
  { code: 'TN', name: 'Tennessee' },
  { code: 'TX', name: 'Texas' },
  { code: 'UT', name: 'Utah' },
  { code: 'VT', name: 'Vermont' },
  { code: 'VA', name: 'Virginia' },
  { code: 'WA', name: 'Washington' },
  { code: 'WV', name: 'West Virginia' },
  { code: 'WI', name: 'Wisconsin' },
  { code: 'WY', name: 'Wyoming' }
];

function TournamentFinder() {
  const [tournaments, setTournaments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showSuggestModal, setShowSuggestModal] = useState(false);

  // Load tournaments from JSON file
  useEffect(() => {
    async function loadTournaments() {
      try {
        setLoading(true);
        const response = await fetch('/tournaments_data.json');
        if (!response.ok) {
          throw new Error('Failed to load tournaments');
        }
        const data = await response.json();
        setTournaments(data.tournaments || []);
        setError(null);
      } catch (err) {
        console.error('Error loading tournaments:', err);
        setError('Unable to load tournaments. Please try again later.');
        setTournaments([]);
      } finally {
        setLoading(false);
      }
    }
    loadTournaments();
  }, []);

  // Filter state
  const [state, setState] = useState('ALL');
  const [gender, setGender] = useState('ALL');
  const [ageGroup, setAgeGroup] = useState('ALL');
  const [level, setLevel] = useState('ALL');
  const [dateRange, setDateRange] = useState('ALL_FUTURE');
  const [searchQuery, setSearchQuery] = useState('');

  // Sorting state
  const [sortField, setSortField] = useState('start_date');
  const [sortDirection, setSortDirection] = useState('asc');

  // Distance filtering from map
  const [distanceFilteredIds, setDistanceFilteredIds] = useState(null);
  const [mapNumbersById, setMapNumbersById] = useState({});

  // Handle column header click for sorting
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      // Default directions: dates asc, games desc, others asc
      setSortDirection(field === 'game_count' ? 'desc' : 'asc');
    }
  };

  // Get sort indicator
  const getSortIndicator = (field) => {
    if (sortField !== field) return '';
    return sortDirection === 'asc' ? ' ▲' : ' ▼';
  };

  // Get unique values for filter dropdowns
  const ageGroups = useMemo(() => {
    const groups = new Set();
    tournaments.forEach(t => {
      if (t.age_groups) {
        // Parse age groups like "U9-U19" or "U13-U15"
        const match = t.age_groups.match(/U(\d+)/g);
        if (match) {
          match.forEach(m => groups.add(m));
        }
      }
    });
    return ['ALL', ...Array.from(groups).sort((a, b) => {
      return parseInt(a.replace('U', '')) - parseInt(b.replace('U', ''));
    })];
  }, [tournaments]);

  const levels = ['ALL', 'Recreational', 'Competitive', 'Showcase', 'Elite'];
  const genders = ['ALL', 'Boys', 'Girls', 'Both'];

  // Handle distance filtering from map
  const handleMapFilter = (filteredTournaments) => {
    if (filteredTournaments === null) {
      setDistanceFilteredIds(null);
      setMapNumbersById({});
    } else {
      setDistanceFilteredIds(new Set(filteredTournaments.map(t => t.event_id)));
      // Build a map of event_id -> mapNumber for display in table
      const numbersMap = {};
      filteredTournaments.forEach(t => {
        if (t.mapNumber) {
          numbersMap[t.event_id] = t.mapNumber;
        }
      });
      setMapNumbersById(numbersMap);
    }
  };

  // Filter tournaments
  const filteredTournaments = useMemo(() => {
    return tournaments.filter(t => {
      // Distance filter from map (if active)
      if (distanceFilteredIds !== null && !distanceFilteredIds.has(t.event_id)) return false;

      // State filter
      if (state !== 'ALL' && t.state !== state) return false;

      // Gender filter
      if (gender !== 'ALL') {
        if (gender === 'Boys' && t.gender === 'Girls') return false;
        if (gender === 'Girls' && t.gender === 'Boys') return false;
      }

      // Age group filter
      if (ageGroup !== 'ALL') {
        const ageNum = parseInt(ageGroup.replace('U', ''));
        const ageMatch = t.age_groups?.match(/U(\d+)-U(\d+)|U(\d+)/);
        if (ageMatch) {
          if (ageMatch[1] && ageMatch[2]) {
            // Range like U9-U19
            const min = parseInt(ageMatch[1]);
            const max = parseInt(ageMatch[2]);
            if (ageNum < min || ageNum > max) return false;
          } else if (ageMatch[3]) {
            // Single age like U14
            if (ageNum !== parseInt(ageMatch[3])) return false;
          }
        }
      }

      // Level filter
      if (level !== 'ALL' && t.level !== level) return false;

      // Date range filter
      if (dateRange !== 'ALL') {
        // Parse the start_date - handle various formats
        let startDate = null;
        if (t.start_date) {
          startDate = new Date(t.start_date);
        } else if (t.dates) {
          // Try to parse from dates field like "December 5-7" or "December 5-7, 2025"
          const dateMatch = t.dates.match(/(\w+)\s+(\d{1,2})(?:-\d{1,2})?(?:,?\s*(\d{4}))?/);
          if (dateMatch) {
            const monthStr = dateMatch[1];
            const day = parseInt(dateMatch[2]);
            const year = dateMatch[3] ? parseInt(dateMatch[3]) : new Date().getFullYear();
            const monthMap = {
              'January': 0, 'February': 1, 'March': 2, 'April': 3,
              'May': 4, 'June': 5, 'July': 6, 'August': 7,
              'September': 8, 'October': 9, 'November': 10, 'December': 11
            };
            const month = monthMap[monthStr];
            if (month !== undefined) {
              startDate = new Date(year, month, day);
            }
          }
        }

        // Skip tournaments without valid dates
        if (!startDate || isNaN(startDate.getTime())) {
          return dateRange === 'ALL_PAST' || dateRange === 'ALL_FUTURE' ? true : false;
        }

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        startDate.setHours(0, 0, 0, 0);

        // Past filters
        if (dateRange === 'ALL_PAST') {
          if (startDate >= today) return false;
        } else if (dateRange === 'PAST_MONTH') {
          const monthAgo = new Date(today);
          monthAgo.setMonth(monthAgo.getMonth() - 1);
          if (startDate >= today || startDate < monthAgo) return false;
        } else if (dateRange === 'PAST_YEAR') {
          const yearAgo = new Date(today);
          yearAgo.setFullYear(yearAgo.getFullYear() - 1);
          if (startDate >= today || startDate < yearAgo) return false;
        }
        // Future filters
        else if (dateRange === 'ALL_FUTURE') {
          if (startDate < today) return false;
        } else if (dateRange === 'NEXT_MONTH') {
          const monthFromNow = new Date(today);
          monthFromNow.setMonth(monthFromNow.getMonth() + 1);
          if (startDate < today || startDate > monthFromNow) return false;
        } else if (dateRange === 'NEXT_3_MONTHS') {
          const threeMonths = new Date(today);
          threeMonths.setMonth(threeMonths.getMonth() + 3);
          if (startDate < today || startDate > threeMonths) return false;
        } else if (dateRange === 'NEXT_YEAR') {
          const yearFromNow = new Date(today);
          yearFromNow.setFullYear(yearFromNow.getFullYear() + 1);
          if (startDate < today || startDate > yearFromNow) return false;
        }
      }

      // Search query
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchName = t.name?.toLowerCase().includes(query);
        const matchCity = t.city?.toLowerCase().includes(query);
        const matchState = t.state?.toLowerCase().includes(query);
        if (!matchName && !matchCity && !matchState) return false;
      }

      return true;
    }).sort((a, b) => {
      let aVal, bVal;

      switch (sortField) {
        case 'name':
          aVal = (a.name || '').toLowerCase();
          bVal = (b.name || '').toLowerCase();
          break;
        case 'sponsor':
          aVal = (a.sponsor || '').toLowerCase();
          bVal = (b.sponsor || '').toLowerCase();
          break;
        case 'city':
          aVal = (a.city || '').toLowerCase();
          bVal = (b.city || '').toLowerCase();
          break;
        case 'state':
          aVal = a.state || '';
          bVal = b.state || '';
          break;
        case 'start_date':
          aVal = a.start_date || '9999-99-99';
          bVal = b.start_date || '9999-99-99';
          break;
        case 'gender':
          aVal = a.gender || '';
          bVal = b.gender || '';
          break;
        case 'age_groups':
          aVal = a.age_groups || '';
          bVal = b.age_groups || '';
          break;
        case 'level':
          aVal = a.level || '';
          bVal = b.level || '';
          break;
        case 'game_count':
          aVal = a.game_count || 0;
          bVal = b.game_count || 0;
          break;
        default:
          aVal = a.start_date || '9999-99-99';
          bVal = b.start_date || '9999-99-99';
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [tournaments, state, gender, ageGroup, level, dateRange, searchQuery, sortField, sortDirection, distanceFilteredIds]);

  return (
    <div className="tournament-finder">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-content">
          <div>
            <h1 className="page-title">Tournament Finder</h1>
            <p className="page-description">
              Search for upcoming soccer tournaments by location, date, age group, and more.
            </p>
          </div>
          <button
            className="btn btn-suggest"
            onClick={() => setShowSuggestModal(true)}
          >
            + Suggest Tournament
          </button>
        </div>
      </div>

      {/* Suggest Tournament Modal */}
      <SuggestTournament
        isOpen={showSuggestModal}
        onClose={() => setShowSuggestModal(false)}
      />

      {/* Filters Card */}
      <div className="card filters-card" style={{ marginBottom: '0.75rem', padding: '0.75rem 1rem' }}>
        <div className="filters-compact">
          {/* Search */}
          <div className="filter-group search-group">
            <input
              type="text"
              className="form-input"
              placeholder="Search by tournament name or city..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Filter Row 1 - When and Age */}
          <div className="filter-row">
            <div className="filter-group">
              <BottomSheetSelect
                label="When"
                value={dateRange}
                onChange={setDateRange}
                options={[
                  { value: 'ALL', label: 'All Dates' },
                  {
                    group: 'Upcoming',
                    options: [
                      { value: 'ALL_FUTURE', label: 'All Upcoming' },
                      { value: 'NEXT_MONTH', label: 'Next Month' },
                      { value: 'NEXT_3_MONTHS', label: 'Next 3 Months' },
                      { value: 'NEXT_YEAR', label: 'Next Year' }
                    ]
                  },
                  {
                    group: 'Past',
                    options: [
                      { value: 'ALL_PAST', label: 'All Past' },
                      { value: 'PAST_MONTH', label: 'Past Month' },
                      { value: 'PAST_YEAR', label: 'Past Year' }
                    ]
                  }
                ]}
              />
            </div>

            <div className="filter-group">
              <BottomSheetSelect
                label="Age"
                value={ageGroup}
                onChange={setAgeGroup}
                options={ageGroups.map(ag => ({
                  value: ag,
                  label: ag === 'ALL' ? 'All Ages' : ag
                }))}
              />
            </div>
          </div>

          {/* Filter Row 2 - State, Gender, Level */}
          <div className="filter-row">
            <div className="filter-group">
              <BottomSheetSelect
                label="State"
                value={state}
                onChange={setState}
                options={US_STATES.map(s => ({
                  value: s.code,
                  label: s.name
                }))}
              />
            </div>

            <div className="filter-group">
              <BottomSheetSelect
                label="Gender"
                value={gender}
                onChange={setGender}
                options={genders.map(g => ({
                  value: g,
                  label: g === 'ALL' ? 'All' : g
                }))}
              />
            </div>

            <div className="filter-group">
              <BottomSheetSelect
                label="Level"
                value={level}
                onChange={setLevel}
                options={levels.map(l => ({
                  value: l,
                  label: l === 'ALL' ? 'All Levels' : l
                }))}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Tournament Map */}
      <TournamentMap
        tournaments={tournaments}
        onFilteredTournaments={handleMapFilter}
      />

      {/* Results */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
          <span className="card-title" style={{ fontSize: '0.9rem' }}>
            {filteredTournaments.length} tournament{filteredTournaments.length !== 1 ? 's' : ''}
            {distanceFilteredIds !== null && <span className="filter-badge"> (filtered by distance)</span>}
          </span>
        </div>

        {loading ? (
          <div className="loading">Loading tournaments...</div>
        ) : error ? (
          <div className="empty-state">
            <div className="empty-state-icon">⚠️</div>
            <p className="empty-state-text">{error}</p>
          </div>
        ) : filteredTournaments.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <p className="empty-state-text">No tournaments match your filters</p>
            <p style={{ color: '#999', fontSize: '0.9rem' }}>
              Try adjusting your search criteria
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table tournaments-table">
              <thead>
                <tr>
                  {Object.keys(mapNumbersById).length > 0 && (
                    <th className="col-map-num">#</th>
                  )}
                  <th
                    className="sortable-header"
                    onClick={() => handleSort('name')}
                    style={{ cursor: 'pointer' }}
                  >
                    Tournament{getSortIndicator('name')}
                  </th>
                  <th
                    className="sortable-header col-sponsor"
                    onClick={() => handleSort('sponsor')}
                    style={{ cursor: 'pointer' }}
                  >
                    Sponsor{getSortIndicator('sponsor')}
                  </th>
                  <th
                    className="sortable-header col-city"
                    onClick={() => handleSort('city')}
                    style={{ cursor: 'pointer' }}
                  >
                    City{getSortIndicator('city')}
                  </th>
                  <th
                    className="sortable-header col-state"
                    onClick={() => handleSort('state')}
                    style={{ cursor: 'pointer' }}
                  >
                    State{getSortIndicator('state')}
                  </th>
                  <th
                    className="sortable-header col-dates"
                    onClick={() => handleSort('start_date')}
                    style={{ cursor: 'pointer' }}
                  >
                    Dates{getSortIndicator('start_date')}
                  </th>
                  <th
                    className="sortable-header col-gender"
                    onClick={() => handleSort('gender')}
                    style={{ cursor: 'pointer' }}
                  >
                    Gender{getSortIndicator('gender')}
                  </th>
                  <th
                    className="sortable-header col-age"
                    onClick={() => handleSort('age_groups')}
                    style={{ cursor: 'pointer' }}
                  >
                    Ages{getSortIndicator('age_groups')}
                  </th>
                  <th
                    className="sortable-header col-level"
                    onClick={() => handleSort('level')}
                    style={{ cursor: 'pointer' }}
                  >
                    Level{getSortIndicator('level')}
                  </th>
                  <th
                    className="sortable-header col-games"
                    onClick={() => handleSort('game_count')}
                    style={{ cursor: 'pointer' }}
                  >
                    Games{getSortIndicator('game_count')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredTournaments.map((tournament) => (
                  <tr key={tournament.event_id}>
                    {Object.keys(mapNumbersById).length > 0 && (
                      <td className="col-map-num">
                        {mapNumbersById[tournament.event_id] || '-'}
                      </td>
                    )}
                    <td className="tournament-name-cell">
                      {(tournament.schedule_url || tournament.website_url) ? (
                        <a
                          href={tournament.schedule_url || tournament.website_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="tournament-link"
                        >
                          {tournament.name}
                        </a>
                      ) : (
                        tournament.name
                      )}
                    </td>
                    <td className="col-sponsor">{tournament.sponsor || '-'}</td>
                    <td className="col-city">{tournament.city || '-'}</td>
                    <td className="col-state">{tournament.state}</td>
                    <td className="col-dates">
                      {tournament.dates}
                      {tournament.start_date && !tournament.dates?.includes('202') && (
                        <span className="date-year"> {tournament.start_date.substring(0, 4)}</span>
                      )}
                    </td>
                    <td className="col-gender">{tournament.gender || 'Both'}</td>
                    <td className="col-age">{tournament.age_groups || '-'}</td>
                    <td className="col-level">{tournament.level || '-'}</td>
                    <td className="col-games">{tournament.game_count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style>{`
        .tournament-finder {
          max-width: 1200px;
          margin: 0 auto;
          box-sizing: border-box;
        }

        .tournament-finder *,
        .tournament-finder *::before,
        .tournament-finder *::after {
          box-sizing: border-box;
        }

        .page-header-content {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1rem;
        }

        .btn-suggest {
          background: var(--accent-green);
          color: white;
          padding: 0.75rem 1.25rem;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          font-size: 0.9rem;
          cursor: pointer;
          transition: all 0.2s ease;
          white-space: nowrap;
        }

        .btn-suggest:hover {
          background: var(--primary-green);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(77, 133, 39, 0.3);
        }

        .table-container {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
        }

        .tournaments-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.9rem;
        }

        .tournaments-table th,
        .tournaments-table td {
          padding: 0.6rem 0.5rem;
          text-align: left;
          border-bottom: 1px solid #e0e0e0;
        }

        .tournaments-table th {
          background: var(--primary-green);
          font-weight: 600;
          color: white;
          white-space: nowrap;
        }

        .tournaments-table tbody tr:hover {
          background: #f5f5f5;
        }

        .sortable-header {
          cursor: pointer;
          user-select: none;
        }

        .sortable-header:hover {
          background: var(--primary-green);
        }

        .tournament-name-cell {
          font-weight: 500;
          max-width: 300px;
        }

        .tournament-link {
          color: var(--primary-green);
          text-decoration: none;
        }

        .tournament-link:hover {
          text-decoration: underline;
          color: var(--accent-green);
        }

        .col-map-num {
          width: 35px;
          text-align: center;
          font-weight: 600;
          color: var(--primary-green);
          background: #e8f5e9;
        }
        .col-sponsor { max-width: 150px; }
        .col-city { max-width: 120px; }
        .col-state { width: 50px; text-align: center; }
        .col-dates { width: 140px; white-space: nowrap; }
        .date-year { color: #666; }
        .col-gender { width: 70px; text-align: center; }
        .col-age { width: 80px; }
        .col-level { width: 90px; }
        .col-games { width: 60px; text-align: center; }

        .filter-badge {
          font-size: 0.8rem;
          font-weight: normal;
          color: var(--primary-green);
          background: #e8f5e9;
          padding: 0.2rem 0.5rem;
          border-radius: 4px;
          margin-left: 0.5rem;
        }

        @media (max-width: 768px) {
          .page-header-content {
            flex-direction: column;
            align-items: stretch;
          }

          .btn-suggest {
            width: 100%;
            text-align: center;
          }

          .tournaments-table {
            font-size: 0.8rem;
          }

          .tournaments-table th,
          .tournaments-table td {
            padding: 0.5rem 0.3rem;
          }

          .tournament-name-cell {
            max-width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .col-gender, .col-level, .col-sponsor, .col-city {
            display: none;
          }
        }

        @media (max-width: 480px) {
          .tournaments-table {
            font-size: 0.75rem;
          }

          .col-age, .col-games {
            display: none;
          }

          .tournament-name-cell {
            max-width: 120px;
          }
        }
      `}</style>
    </div>
  );
}

export default TournamentFinder;
