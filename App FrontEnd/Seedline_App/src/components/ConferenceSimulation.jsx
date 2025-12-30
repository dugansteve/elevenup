import { useState, useMemo, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useRankingsData } from '../data/useRankingsData';
import BottomSheetSelect from './BottomSheetSelect';

// Simulation constants
const N_SIMULATIONS = 10000;
const HOME_ADVANTAGE = 30; // Elo-style home advantage points
const SEASON_START_DATE = new Date('2025-08-01'); // Games before this date are previous season

// League categorization
const NATIONAL_LEAGUES = ['ECNL', 'ECNL-RL', 'GA', 'ASPIRE', 'NPL', 'MLS NEXT', 'MLS NEXT HD', 'MLS NEXT AD'];
const REGIONAL_LEAGUES = [
  'Baltimore Mania',
  'Chesapeake PSL YPL',
  'Eastern PA Challenge Cup',
  'Florida CFPL',
  'Florida NFPL',
  'Florida SEFPL',
  'Florida WFPL',
  'ICSL',
  'Illinois Cup',
  'Mid South Conference',
  'MSPSP',
  'Northwest Conference',
  'Presidents Cup',
  'Real CO Cup',
  'SEFPL',
  'SLYSA',
  'SOCAL',
  'Southeastern CCL Fall',
  'Southeastern CCL U11/U12',
  'State Cup',
  'Virginia Cup',
  'WFPL',
  'WVFC Capital Cup'
];

// Parse game date from various formats
function parseGameDate(dateStr) {
  if (!dateStr) return null;

  // Try ISO format first (YYYY-MM-DD)
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    return new Date(dateStr);
  }

  // Try "Mon D, YYYY" format (e.g., "Sep 6, 2025")
  const parsed = new Date(dateStr);
  if (!isNaN(parsed.getTime())) {
    return parsed;
  }

  return null;
}

// Helper function for league badge colors
function getLeagueBadgeStyle(league) {
  const styles = {
    'ECNL': { background: '#e3f2fd', color: '#1976d2' },
    'GA': { background: '#f3e5f5', color: '#7b1fa2' },
    'ECNL-RL': { background: '#ffebee', color: '#c62828' },
    'ASPIRE': { background: '#e8f5e9', color: '#2e7d32' },
    'NPL': { background: '#fff3e0', color: '#e65100' },
    'MLS NEXT HD': { background: '#006064', color: '#ffffff' },  // Dark Teal (MLS pro clubs - Homegrown Division)
    'MLS NEXT AD': { background: '#e0f7fa', color: '#00838f' },  // Light Teal (Academy Division)
  };
  return styles[league] || { background: '#f5f5f5', color: '#666' };
}

// Helper function to normalize conference names by stripping age suffixes
function normalizeConference(conference) {
  if (!conference) return conference;
  // Strip age suffixes like "U11", "U12", "U13", "U14", "U15", "U16", "U17", "U18", "U19"
  // Also handles variations with spaces or dashes
  return conference
    .replace(/\s*[-\s]?\s*U1[0-9]\s*$/i, '')
    .trim();
}

// Check if a conference name indicates an event (national, showcase, playoff, etc.)
// vs regular league play
function isEventConference(conference) {
  if (!conference) return false;
  const confLower = conference.toLowerCase();
  return confLower.includes('national') ||
    confLower.includes('showcase') ||
    confLower.includes('playoff') ||
    confLower.includes('cup') ||
    confLower.includes('championship') ||
    confLower.includes('regional event');
}

// Helper function to sort age groups numerically
function sortAgeGroupsNumerically(ageGroups) {
  return [...ageGroups].sort((a, b) => {
    const getNum = (ag) => {
      const match = ag.match(/\d+/);
      return match ? parseInt(match[0], 10) : 0;
    };
    return getNum(a) - getNum(b);
  });
}

// Calculate win probability using Elo-style formula
function calculateWinProbability(teamAPower, teamBPower, homeAdvantage = 0) {
  const diff = teamAPower - teamBPower + homeAdvantage;
  const prob = 1 / (1 + Math.pow(10, -diff / 400));
  return prob;
}

// Simulate a single game
function simulateGame(homeTeam, awayTeam) {
  const winProb = calculateWinProbability(
    homeTeam.powerScore || 1500,
    awayTeam.powerScore || 1500,
    HOME_ADVANTAGE
  );

  // Add variance based on predictability and base upset factor
  // Predictability is 0-100 (percentage), convert to 0-1 range
  const homePred = (homeTeam.predictability || 50) / 100;
  const awayPred = (awayTeam.predictability || 50) / 100;
  const uncertainty = 1 - (homePred + awayPred) / 2;

  // Add random variance for upset potential
  let adjustedProb = winProb + (Math.random() - 0.5) * uncertainty * 0.6;

  // Ensure significant upset chance - any team can beat any team on a given day
  // Heavy favorites have ~8% chance of losing, underdogs have ~8% chance of winning
  const MIN_WIN_PROB = 0.08;
  const MAX_WIN_PROB = 0.92;
  adjustedProb = Math.max(MIN_WIN_PROB, Math.min(MAX_WIN_PROB, adjustedProb));

  const random = Math.random();

  // Determine outcome (simplified: win/draw/loss based on probability)
  const drawProb = 0.15; // ~15% draw probability
  if (random < adjustedProb - drawProb / 2) {
    return { homeWin: true, awayWin: false, draw: false };
  } else if (random > adjustedProb + drawProb / 2) {
    return { homeWin: false, awayWin: true, draw: false };
  } else {
    return { homeWin: false, awayWin: false, draw: true };
  }
}

// Clean team name for matching (strip age codes, league suffixes, etc.)
// This mirrors the ranker's team name cleaning logic
function cleanTeamName(teamName) {
  if (!teamName) return teamName;
  let result = teamName;

  // Remove age patterns: "13G", "12B", "2011G", "G13", "G2011", "08/07G"
  result = result.replace(/\s+\d{2}[GB](?=\s|$)/gi, '');
  result = result.replace(/\s+20\d{2}[GB](?=\s|$)/gi, '');
  result = result.replace(/\s+[GB]\d{2}(?=\s|$)/gi, '');
  result = result.replace(/\s+[GB]20\d{2}(?=\s|$)/gi, '');
  result = result.replace(/\s+\d{2}\/\d{2}[GB](?=\s|$)/gi, '');

  // Remove "2011", "2012", etc. birth years
  result = result.replace(/\s+20(0[6-9]|1[0-9])(?=\s|$)/g, '');

  // Remove "11 Girls", "12 Boys", etc.
  result = result.replace(/\s+\d{2}\s+(Girls?|Boys?)(?=\s|$)/gi, '');

  // Remove league suffixes: "NPL", "ECNL", "GA", "Aspire", "Academy", "Premier", "Elite"
  result = result.replace(/\s+(NPL|ECNL|ECNL-RL|GA|Aspire|Academy|Premier|Elite|Pre-Academy|Pre GA|Pre-GA)(?=\s|$)/gi, '');

  // Remove U-age patterns: "(U15)", "U14", etc.
  result = result.replace(/\s*\(U\d+\)/gi, '');
  result = result.replace(/\s+U\d+(?=\s|$)/gi, '');

  // Remove trailing designators after dash: "- Zahn", "- Smith", etc.
  result = result.replace(/\s+-\s+\w+$/gi, '');

  // Remove color/level suffixes: "White", "Blue", "Gold", "Red", etc.
  result = result.replace(/\s+(White|Blue|Gold|Red|Black|Green|Orange|Purple|Silver|Gray|Navy)(?=\s|$)/gi, '');

  // Normalize multiple spaces
  result = result.replace(/\s+/g, ' ').trim();

  return result;
}

// Build team lookup by name for matching games to teams
function buildTeamLookup(teams) {
  const lookup = {};
  teams.forEach(team => {
    // Store by exact name
    lookup[team.name] = team;
    lookup[team.name.toLowerCase()] = team;
    // Also store by cleaned name for fuzzy matching
    const cleaned = cleanTeamName(team.name);
    lookup[cleaned] = team;
    lookup[cleaned.toLowerCase()] = team;
  });
  return lookup;
}

// Find team in lookup, trying various name formats
function findTeam(teamLookup, gameTeamName) {
  if (!gameTeamName) return null;

  // Try exact match first
  if (teamLookup[gameTeamName]) return teamLookup[gameTeamName];
  if (teamLookup[gameTeamName.toLowerCase()]) return teamLookup[gameTeamName.toLowerCase()];

  // Try cleaned name
  const cleaned = cleanTeamName(gameTeamName);
  if (teamLookup[cleaned]) return teamLookup[cleaned];
  if (teamLookup[cleaned.toLowerCase()]) return teamLookup[cleaned.toLowerCase()];

  return null;
}

// Run Monte Carlo simulation with actual game results
function runSimulation(teams, completedGames, upcomingGames, numSimulations = N_SIMULATIONS) {
  if (teams.length === 0) return { results: [], stats: {} };

  const teamLookup = buildTeamLookup(teams);

  // Initialize tracking
  const champCounts = {};
  const topThreeCounts = {};
  const positionSums = {};
  const remainingWinsSums = {};
  const remainingLossesSums = {};
  const remainingDrawsSums = {};

  teams.forEach(team => {
    champCounts[team.id] = 0;
    topThreeCounts[team.id] = 0;
    positionSums[team.id] = 0;
    remainingWinsSums[team.id] = 0;
    remainingLossesSums[team.id] = 0;
    remainingDrawsSums[team.id] = 0;
  });

  // Calculate standings from completed games (this is fixed, not simulated)
  const baseStandings = {};
  teams.forEach(team => {
    baseStandings[team.id] = {
      points: 0,
      wins: 0,
      losses: 0,
      draws: 0,
      goalsFor: 0,
      goalsAgainst: 0
    };
  });

  // Apply completed game results to base standings
  completedGames.forEach(game => {
    const homeTeam = findTeam(teamLookup, game.homeTeam);
    const awayTeam = findTeam(teamLookup, game.awayTeam);

    if (!homeTeam || !awayTeam) return; // Skip if team not in our list

    const homeScore = game.homeScore;
    const awayScore = game.awayScore;

    // Update goals
    baseStandings[homeTeam.id].goalsFor += homeScore;
    baseStandings[homeTeam.id].goalsAgainst += awayScore;
    baseStandings[awayTeam.id].goalsFor += awayScore;
    baseStandings[awayTeam.id].goalsAgainst += homeScore;

    // Update results
    if (homeScore > awayScore) {
      baseStandings[homeTeam.id].wins += 1;
      baseStandings[homeTeam.id].points += 3;
      baseStandings[awayTeam.id].losses += 1;
    } else if (awayScore > homeScore) {
      baseStandings[awayTeam.id].wins += 1;
      baseStandings[awayTeam.id].points += 3;
      baseStandings[homeTeam.id].losses += 1;
    } else {
      baseStandings[homeTeam.id].draws += 1;
      baseStandings[homeTeam.id].points += 1;
      baseStandings[awayTeam.id].draws += 1;
      baseStandings[awayTeam.id].points += 1;
    }
  });

  // Filter upcoming games to only those involving our teams
  const relevantUpcoming = upcomingGames.filter(game => {
    const homeTeam = findTeam(teamLookup, game.homeTeam);
    const awayTeam = findTeam(teamLookup, game.awayTeam);
    return homeTeam && awayTeam;
  });

  // Run simulations
  for (let sim = 0; sim < numSimulations; sim++) {
    // Start with base standings (from completed games)
    const simStandings = {};
    // Track remaining record for this simulation
    const simRemainingRecord = {};
    teams.forEach(team => {
      simStandings[team.id] = { ...baseStandings[team.id] };
      simRemainingRecord[team.id] = { wins: 0, losses: 0, draws: 0 };
    });

    // Simulate only upcoming/remaining games
    relevantUpcoming.forEach(game => {
      const homeTeam = findTeam(teamLookup, game.homeTeam);
      const awayTeam = findTeam(teamLookup, game.awayTeam);

      if (!homeTeam || !awayTeam) return;

      const result = simulateGame(homeTeam, awayTeam);

      if (result.homeWin) {
        simStandings[homeTeam.id].points += 3;
        simStandings[homeTeam.id].wins += 1;
        simStandings[homeTeam.id].goalsFor += 1;
        simStandings[awayTeam.id].goalsAgainst += 1;
        simStandings[awayTeam.id].losses += 1;
        // Track remaining record
        simRemainingRecord[homeTeam.id].wins += 1;
        simRemainingRecord[awayTeam.id].losses += 1;
      } else if (result.awayWin) {
        simStandings[awayTeam.id].points += 3;
        simStandings[awayTeam.id].wins += 1;
        simStandings[awayTeam.id].goalsFor += 1;
        simStandings[homeTeam.id].goalsAgainst += 1;
        simStandings[homeTeam.id].losses += 1;
        // Track remaining record
        simRemainingRecord[awayTeam.id].wins += 1;
        simRemainingRecord[homeTeam.id].losses += 1;
      } else {
        simStandings[homeTeam.id].points += 1;
        simStandings[homeTeam.id].draws += 1;
        simStandings[awayTeam.id].points += 1;
        simStandings[awayTeam.id].draws += 1;
        // Track remaining record
        simRemainingRecord[homeTeam.id].draws += 1;
        simRemainingRecord[awayTeam.id].draws += 1;
      }
    });

    // Sort teams by points per game (then goal diff for tiebreaker)
    const sortedTeams = [...teams].sort((a, b) => {
      const statsA = simStandings[a.id];
      const statsB = simStandings[b.id];
      const gamesA = statsA.wins + statsA.losses + statsA.draws;
      const gamesB = statsB.wins + statsB.losses + statsB.draws;
      const ppgA = gamesA > 0 ? statsA.points / gamesA : 0;
      const ppgB = gamesB > 0 ? statsB.points / gamesB : 0;
      if (ppgB !== ppgA) return ppgB - ppgA;
      // Tiebreaker: goal differential
      const gdA = statsA.goalsFor - statsA.goalsAgainst;
      const gdB = statsB.goalsFor - statsB.goalsAgainst;
      return gdB - gdA;
    });

    // Track championship winner, positions, and remaining record sums
    sortedTeams.forEach((team, position) => {
      if (position === 0) champCounts[team.id]++;
      if (position < 3) topThreeCounts[team.id]++;
      positionSums[team.id] += position + 1;
      remainingWinsSums[team.id] += simRemainingRecord[team.id].wins;
      remainingLossesSums[team.id] += simRemainingRecord[team.id].losses;
      remainingDrawsSums[team.id] += simRemainingRecord[team.id].draws;
    });
  }

  // Calculate final probabilities and stats
  const results = teams.map(team => ({
    ...team,
    currentStandings: baseStandings[team.id],
    champProbability: (champCounts[team.id] / numSimulations * 100).toFixed(1),
    topThreeProbability: (topThreeCounts[team.id] / numSimulations * 100).toFixed(1),
    avgPosition: (positionSums[team.id] / numSimulations).toFixed(1),
    expectedRemainingWins: (remainingWinsSums[team.id] / numSimulations).toFixed(1),
    expectedRemainingLosses: (remainingLossesSums[team.id] / numSimulations).toFixed(1),
    expectedRemainingDraws: (remainingDrawsSums[team.id] / numSimulations).toFixed(1),
  }));

  // Sort by average finish position (lower is better)
  results.sort((a, b) => parseFloat(a.avgPosition) - parseFloat(b.avgPosition));

  const stats = {
    completedGamesUsed: completedGames.length,
    upcomingGamesToSimulate: relevantUpcoming.length,
    simulationsRun: numSimulations
  };

  return { results, stats };
}

function ConferenceSimulation() {
  const { teamsData, ageGroups, leagues, isLoading, error } = useRankingsData();

  // Game data state
  const [gamesData, setGamesData] = useState(null);
  const [gamesLoading, setGamesLoading] = useState(true);
  const [gamesError, setGamesError] = useState(null);

  // Filter state
  const [selectedLeague, setSelectedLeague] = useState('');
  const [selectedAgeGroup, setSelectedAgeGroup] = useState('');
  const [selectedGender, setSelectedGender] = useState('');
  const [selectedConference, setSelectedConference] = useState('');
  const [showGenderAgeSheet, setShowGenderAgeSheet] = useState(false);

  // Simulation state
  const [simulationResults, setSimulationResults] = useState(null);
  const [simulationStats, setSimulationStats] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);

  // Load conference games data ONLY when user clicks to load it (lazy loading)
  const loadGamesData = useCallback(() => {
    if (gamesData) return; // Already loaded

    setGamesLoading(true);
    // Add cache-busting timestamp to ensure fresh data
    fetch(`/conference_games.json?v=${Date.now()}`)
      .then(res => {
        if (!res.ok) throw new Error('Conference games data not found');
        return res.json();
      })
      .then(data => {
        setGamesData(data);
        setGamesLoading(false);
      })
      .catch(err => {
        console.warn('Could not load conference games:', err);
        setGamesError('Game data not available - simulation will use estimated matchups');
        setGamesLoading(false);
      });
  }, [gamesData]);

  // Don't auto-load on mount - wait for user interaction
  useEffect(() => {
    // Set loading to false initially since we're not loading yet
    setGamesLoading(false);
  }, []);

  // Get available conferences based on current filters (normalized to remove age suffixes)
  const availableConferences = useMemo(() => {
    if (!selectedLeague || !selectedAgeGroup) return [];

    const genderPrefix = selectedGender === 'Girls' ? 'G' : selectedGender === 'Boys' ? 'B' : '';

    const conferences = new Set();
    teamsData.forEach(team => {
      if (team.league === selectedLeague &&
        team.ageGroup === selectedAgeGroup &&
        team.conference &&
        (genderPrefix === '' || team.ageGroup?.startsWith(genderPrefix))) {
        // Normalize conference name to remove age suffixes like "U15"
        conferences.add(normalizeConference(team.conference));
      }
    });

    return [...conferences].sort();
  }, [teamsData, selectedLeague, selectedAgeGroup, selectedGender]);

  // Get teams in selected conference (using normalized conference matching)
  const conferenceTeams = useMemo(() => {
    if (!selectedLeague || !selectedAgeGroup) return [];

    return teamsData.filter(team => {
      const matchesLeague = team.league === selectedLeague;
      const matchesAge = team.ageGroup === selectedAgeGroup;
      // Match using normalized conference names
      const matchesConference = !selectedConference ||
        normalizeConference(team.conference) === selectedConference;
      return matchesLeague && matchesAge && matchesConference;
    }).sort((a, b) => (b.powerScore || 0) - (a.powerScore || 0));
  }, [teamsData, selectedLeague, selectedAgeGroup, selectedConference]);

  // Get games for selected conference (only games from current season - after Aug 1)
  const { completedGames, upcomingGames } = useMemo(() => {
    if (!gamesData || !selectedLeague || !selectedAgeGroup) {
      return { completedGames: [], upcomingGames: [] };
    }

    const filterGames = (games) => games.filter(game => {
      const matchesLeague = game.league === selectedLeague;
      const matchesAge = game.ageGroup === selectedAgeGroup;

      // Only include games from current season (after Aug 1)
      const gameDate = parseGameDate(game.date || game.gameDate);
      const isCurrentSeason = !gameDate || gameDate >= SEASON_START_DATE;

      if (!matchesLeague || !matchesAge || !isCurrentSeason) return false;

      // If no conference selected ("All in League/Age"): include ALL games (league + events)
      if (!selectedConference) return true;

      // If specific conference selected: only include league games from that conference
      // (exclude national/showcase/playoff events)
      const normalizedGameConf = normalizeConference(game.conference);
      const matchesConference = normalizedGameConf === selectedConference;
      const isLeagueGame = !isEventConference(game.conference);

      return matchesConference && isLeagueGame;
    });

    return {
      completedGames: filterGames(gamesData.completedGames || []),
      upcomingGames: filterGames(gamesData.upcomingGames || [])
    };
  }, [gamesData, selectedLeague, selectedAgeGroup, selectedConference]);


  // Run simulation - loads games data first if needed
  const handleRunSimulation = useCallback(() => {
    if (conferenceTeams.length < 2) return;

    // If games data not loaded yet, load it first then run simulation
    if (!gamesData) {
      setIsSimulating(true);
      // Add cache-busting timestamp to ensure fresh data
      fetch(`/conference_games.json?v=${Date.now()}`)
        .then(res => {
          if (!res.ok) throw new Error('Conference games data not found');
          return res.json();
        })
        .then(data => {
          setGamesData(data);
          setGamesLoading(false);
          // Now run simulation with loaded data (only games from current season)
          // Filter logic: "All in League/Age" includes all games, specific conference = league games only
          const filterGameForSim = (game) => {
            const matchesLeague = game.league === selectedLeague;
            const matchesAge = game.ageGroup === selectedAgeGroup;
            const gameDate = parseGameDate(game.date || game.gameDate);
            const isCurrentSeason = !gameDate || gameDate >= SEASON_START_DATE;
            if (!matchesLeague || !matchesAge || !isCurrentSeason) return false;
            if (!selectedConference) return true; // All games for "All in League/Age"
            // Specific conference: league games only (no events)
            const normalizedGameConf = normalizeConference(game.conference);
            const matchesConference = normalizedGameConf === selectedConference;
            const isLeagueGame = !isEventConference(game.conference);
            return matchesConference && isLeagueGame;
          };
          const filteredCompleted = (data.completedGames || []).filter(filterGameForSim);
          const filteredUpcoming = (data.upcomingGames || []).filter(filterGameForSim);
          const { results, stats } = runSimulation(conferenceTeams, filteredCompleted, filteredUpcoming);
          setSimulationResults(results);
          setSimulationStats(stats);
          setIsSimulating(false);
        })
        .catch(err => {
          console.warn('Could not load conference games:', err);
          setGamesError('Game data not available - running simulation without historical data');
          // Run simulation without games data
          const { results, stats } = runSimulation(conferenceTeams, [], []);
          setSimulationResults(results);
          setSimulationStats(stats);
          setIsSimulating(false);
        });
      return;
    }

    setIsSimulating(true);

    // Use setTimeout to allow UI to update
    setTimeout(() => {
      const { results, stats } = runSimulation(
        conferenceTeams,
        completedGames,
        upcomingGames
      );
      setSimulationResults(results);
      setSimulationStats(stats);
      setIsSimulating(false);
    }, 100);
  }, [conferenceTeams, completedGames, upcomingGames, gamesData, selectedLeague, selectedAgeGroup, selectedConference]);

  // Reset simulation when filters change
  const handleFilterChange = useCallback((setter, value) => {
    setter(value);
    setSimulationResults(null);
    setSimulationStats(null);
  }, []);

  if (isLoading) {
    return (
      <div className="card">
        <div className="loading">Loading rankings data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">!</div>
          <div className="empty-state-text">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="card" style={{ marginBottom: '0.75rem', padding: '1rem 1.25rem' }}>
        <h1 style={{
          margin: 0,
          fontSize: '1.5rem',
          fontWeight: '700',
          color: 'var(--primary-green)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          Conference Simulation
        </h1>
        <p style={{ margin: '0.5rem 0 0 0', color: '#666', fontSize: '0.9rem' }}>
          Run Monte Carlo simulations using actual game results to predict final standings
        </p>
        {gamesError && (
          <p style={{ margin: '0.5rem 0 0 0', color: '#e65100', fontSize: '0.85rem' }}>
            Note: {gamesError}
          </p>
        )}
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: '0.75rem', padding: '1rem 1.25rem' }}>
        <div className="sim-filters" style={{ marginBottom: '1rem' }}>
          {/* Gender/Age Combined */}
          <div className="filter-group">
            <label className="filter-label">Gender/Age</label>
            <button
              className="filter-select mobile-filter-btn"
              onClick={() => setShowGenderAgeSheet(true)}
              style={{
                textAlign: 'left',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                padding: '0.5rem 0.75rem',
                border: '1px solid #ddd',
                borderRadius: '8px',
                background: 'white',
                fontSize: '0.9rem'
              }}
            >
              <span>
                {selectedAgeGroup || 'Select'}
              </span>
              <span style={{ marginLeft: '0.5rem', opacity: 0.6 }}>▼</span>
            </button>
          </div>

          {/* League */}
          <div className="filter-group">
            <label className="filter-label">League</label>
            <BottomSheetSelect
              label="League"
              value={selectedLeague}
              onChange={(val) => {
                handleFilterChange(setSelectedLeague, val);
                setSelectedConference('');
              }}
              placeholder="Select League"
              options={[
                { value: '', label: 'Select League' },
                {
                  group: 'National Leagues',
                  options: NATIONAL_LEAGUES.filter(l => leagues.includes(l)).map(league => ({
                    value: league,
                    label: league
                  }))
                },
                {
                  group: 'Regional Leagues',
                  options: REGIONAL_LEAGUES.filter(l => leagues.includes(l)).map(league => ({
                    value: league,
                    label: league
                  }))
                }
              ].filter(opt => !opt.group || opt.options.length > 0)}
            />
          </div>

          {/* Conference */}
          <div className="filter-group">
            <label className="filter-label">Conference</label>
            <BottomSheetSelect
              label="Conference"
              value={selectedConference}
              onChange={(val) => handleFilterChange(setSelectedConference, val)}
              placeholder={availableConferences.length === 0 ? 'No conferences' : 'All in League/Age'}
              options={[
                { value: '', label: 'All in League/Age' },
                ...availableConferences.map(conf => ({
                  value: conf,
                  label: conf
                }))
              ]}
            />
          </div>
        </div>

        {/* Game stats info */}
        {selectedLeague && selectedAgeGroup && (
          <div style={{
            display: 'flex',
            gap: '1.5rem',
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            background: '#f8f9fa',
            borderRadius: '8px',
            flexWrap: 'wrap'
          }}>
            <div>
              <span style={{ color: '#666', fontSize: '0.85rem' }}>Completed Games: </span>
              <span style={{ fontWeight: '600', color: '#2e7d32' }}>{completedGames.length}</span>
            </div>
            <div>
              <span style={{ color: '#666', fontSize: '0.85rem' }}>Upcoming Games: </span>
              <span style={{ fontWeight: '600', color: '#1976d2' }}>{upcomingGames.length}</span>
            </div>
            <div>
              <span style={{ color: '#666', fontSize: '0.85rem' }}>Teams: </span>
              <span style={{ fontWeight: '600' }}>{conferenceTeams.length}</span>
            </div>
          </div>
        )}

        {/* Run Simulation Button */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', alignItems: 'center' }}>
          <button
            onClick={handleRunSimulation}
            disabled={conferenceTeams.length < 2 || isSimulating}
            className="btn btn-primary"
            style={{
              padding: '0.75rem 2rem',
              fontSize: '1rem',
              opacity: conferenceTeams.length < 2 ? 0.5 : 1
            }}
          >
            {isSimulating ? 'Running Simulation...' : `Run Simulation (${N_SIMULATIONS.toLocaleString()} iterations)`}
          </button>
        </div>
      </div>

      {/* Current Standings (before simulation) */}
      {!simulationResults && conferenceTeams.length > 0 && completedGames.length > 0 && (
        <div className="card" style={{ marginBottom: '0.75rem' }}>
          <div className="card-header">
            <h2 className="card-title">Current Standings (from {completedGames.length} games played)</h2>
          </div>
          <div className="scroll-hint" style={{ fontSize: '0.75rem', color: '#888', marginBottom: '0.25rem' }}>
            Swipe to see more columns
          </div>
          <div className="table-scroll-container">
            <table className="data-table simulation-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>#</th>
                  <th>Team</th>
                  <th>Conference</th>
                  <th style={{ textAlign: 'center' }}>Power</th>
                  <th style={{ textAlign: 'center' }}>Record</th>
                </tr>
              </thead>
              <tbody>
                {conferenceTeams.map((team, idx) => (
                  <tr key={team.id}>
                    <td>{idx + 1}</td>
                    <td>
                      <Link
                        to={`/team/${team.id}`}
                        style={{ color: 'var(--primary-green)', textDecoration: 'none', fontWeight: '500' }}
                      >
                        {team.name} {team.ageGroup}
                      </Link>
                    </td>
                    <td style={{ color: '#666', fontSize: '0.85rem' }}>{team.conference || '-'}</td>
                    <td style={{ textAlign: 'center', fontWeight: '600' }}>
                      {team.powerScore?.toFixed(1) || '-'}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {team.wins}-{team.losses}-{team.draws}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Teams Preview (no games data) */}
      {!simulationResults && conferenceTeams.length > 0 && completedGames.length === 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Teams in {selectedConference || 'Selected Group'}</h2>
          </div>
          <div className="scroll-hint" style={{ fontSize: '0.75rem', color: '#888', marginBottom: '0.25rem' }}>
            Swipe to see more columns
          </div>
          <div className="table-scroll-container">
            <table className="data-table simulation-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>#</th>
                  <th>Team</th>
                  <th>Conference</th>
                  <th style={{ textAlign: 'center' }}>Power</th>
                  <th style={{ textAlign: 'center' }}>Record</th>
                </tr>
              </thead>
              <tbody>
                {conferenceTeams.map((team, idx) => (
                  <tr key={team.id}>
                    <td>{idx + 1}</td>
                    <td>
                      <Link
                        to={`/team/${team.id}`}
                        style={{ color: 'var(--primary-green)', textDecoration: 'none', fontWeight: '500' }}
                      >
                        {team.name} {team.ageGroup}
                      </Link>
                    </td>
                    <td style={{ color: '#666', fontSize: '0.85rem' }}>{team.conference || '-'}</td>
                    <td style={{ textAlign: 'center', fontWeight: '600' }}>
                      {team.powerScore?.toFixed(1) || '-'}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {team.wins}-{team.losses}-{team.draws}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Simulation Results */}
      {simulationResults && (
        <div className="card">
          <div className="card-header" style={{
            background: 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)',
            color: 'white',
            borderRadius: '8px 8px 0 0',
            margin: '-1rem -1rem 1rem -1rem',
            padding: '1rem 1.25rem'
          }}>
            <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600' }}>
              Simulation Results - {selectedConference || selectedLeague} {selectedAgeGroup}
            </h2>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', opacity: 0.9 }}>
              {simulationStats?.completedGamesUsed || 0} games played +{' '}
              {simulationStats?.upcomingGamesToSimulate || 0} games simulated ({N_SIMULATIONS.toLocaleString()}x)
            </p>
          </div>

          <div className="scroll-hint" style={{ fontSize: '0.75rem', color: '#888', marginBottom: '0.25rem' }}>
            Swipe to see more columns
          </div>
          <div className="table-scroll-container">
            <table className="data-table simulation-table">
              <thead>
                <tr>
                  <th style={{ width: '45px', minWidth: '45px' }}>Proj.</th>
                  <th style={{ minWidth: '100px' }}>Team</th>
                  <th style={{ textAlign: 'center', minWidth: '55px' }}>Power</th>
                  <th style={{ textAlign: 'center', minWidth: '70px' }}>Current</th>
                  <th style={{ textAlign: 'center', minWidth: '85px', background: '#e8f5e9', color: '#2e7d32' }}>Exp. Rem.</th>
                  <th style={{ textAlign: 'center', background: '#fff3e0', color: '#e65100', minWidth: '65px' }}>Champ %</th>
                  <th style={{ textAlign: 'center', background: '#e3f2fd', color: '#1565c0', minWidth: '60px' }}>Top 3 %</th>
                  <th style={{ textAlign: 'center', minWidth: '55px' }}>Avg Fin</th>
                </tr>
              </thead>
              <tbody>
                {simulationResults.map((team, idx) => {
                  const standings = team.currentStandings || {};
                  return (
                    <tr key={team.id}>
                      <td style={{
                        fontWeight: '700',
                        color: idx === 0 ? '#ffc107' : idx < 3 ? 'var(--primary-green)' : '#666',
                        fontSize: idx === 0 ? '1.1rem' : '0.95rem'
                      }}>
                        {idx === 0 ? '1st' : idx === 1 ? '2nd' : idx === 2 ? '3rd' : `${idx + 1}th`}
                      </td>
                      <td>
                        <Link
                          to={`/team/${team.id}`}
                          style={{ color: 'var(--primary-green)', textDecoration: 'none', fontWeight: '500' }}
                        >
                          {team.name} {team.ageGroup}
                        </Link>
                        <div style={{ fontSize: '0.8rem', color: '#888' }}>{team.conference}</div>
                      </td>
                      <td style={{ textAlign: 'center', fontWeight: '600' }}>
                        {team.powerScore?.toFixed(1) || '-'}
                      </td>
                      <td style={{ textAlign: 'center', fontSize: '0.9rem' }}>
                        {standings.wins || 0}-{standings.losses || 0}-{standings.draws || 0}
                        <div style={{ fontSize: '0.75rem', color: '#888' }}>
                          {standings.points || 0} pts
                        </div>
                      </td>
                      <td style={{ textAlign: 'center', fontSize: '0.85rem', background: '#e8f5e9', fontWeight: '500' }}>
                        {team.expectedRemainingWins}-{team.expectedRemainingLosses}-{team.expectedRemainingDraws}
                      </td>
                      <td style={{
                        textAlign: 'center',
                        fontWeight: '700',
                        fontSize: '1.1rem',
                        color: parseFloat(team.champProbability) > 20 ? '#e65100' :
                          parseFloat(team.champProbability) > 10 ? '#f57c00' : '#666',
                        background: '#fff3e0'
                      }}>
                        {team.champProbability}%
                      </td>
                      <td style={{
                        textAlign: 'center',
                        fontWeight: '600',
                        color: parseFloat(team.topThreeProbability) > 50 ? '#1976d2' : '#666',
                        background: '#e3f2fd'
                      }}>
                        {team.topThreeProbability}%
                      </td>
                      <td style={{ textAlign: 'center', color: '#666' }}>
                        {team.avgPosition}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Methodology Note */}
          <div style={{
            marginTop: '1.5rem',
            padding: '1rem',
            background: '#f8f9fa',
            borderRadius: '8px',
            fontSize: '0.85rem',
            color: '#666'
          }}>
            <strong>Methodology:</strong> This simulation uses actual <em>conference</em> game results only.
            Tournament and showcase games (Champions Cup, Playoffs, etc.) are excluded to accurately
            reflect conference standings. Remaining games are simulated using Monte Carlo methods
            with Elo-style win probability calculations based on team power scores.
            {simulationStats?.completedGamesUsed > 0 ? (
              <span> {simulationStats.completedGamesUsed} completed conference games are locked in; {simulationStats.upcomingGamesToSimulate} remaining games were simulated {N_SIMULATIONS.toLocaleString()} times each.</span>
            ) : (
              <span> No completed conference games found - full season was simulated.</span>
            )}
          </div>
        </div>
      )}

      {/* Empty state */}
      {conferenceTeams.length === 0 && selectedLeague && selectedAgeGroup && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">?</div>
            <div className="empty-state-text">No teams found for this selection</div>
            <p style={{ color: '#888', marginTop: '0.5rem' }}>
              Try selecting a different league, age group, or conference
            </p>
          </div>
        </div>
      )}

      {/* Initial prompt */}
      {!selectedLeague && !selectedAgeGroup && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon" style={{ fontSize: '3rem' }}>?</div>
            <div className="empty-state-text">Select filters to begin</div>
            <p style={{ color: '#888', marginTop: '0.5rem' }}>
              Choose a gender, age group, and league to see teams and run simulations
            </p>
          </div>
        </div>
      )}

      {/* Gender/Age Bottom Sheet */}
      {showGenderAgeSheet && (
        <div
          className="bottom-sheet-overlay"
          onClick={() => setShowGenderAgeSheet(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 3000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem'
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'white',
              borderRadius: '16px',
              width: '100%',
              maxWidth: '600px',
              maxHeight: '85vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
            }}
          >
            {/* Header */}
            <div style={{
              padding: '1rem 1.25rem',
              borderBottom: '1px solid #e0e0e0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexShrink: 0
            }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', color: 'var(--primary-green)' }}>
                Select Gender/Age
              </h3>
              <button
                onClick={() => setShowGenderAgeSheet(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  color: '#666',
                  padding: '0.25rem',
                  lineHeight: 1
                }}
              >
                ×
              </button>
            </div>

            {/* Options */}
            <div style={{
              flex: 1,
              overflowY: 'auto',
              padding: '1rem 1.25rem'
            }}>
              {/* Two-column layout for Girls and Boys */}
              <div style={{
                display: 'flex',
                gap: '1rem'
              }}>
                {/* Girls Column */}
                <div style={{ flex: 1 }}>
                  <div style={{
                    padding: '0.5rem 0',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    color: '#888',
                    textTransform: 'uppercase',
                    borderBottom: '1px solid #eee',
                    marginBottom: '0.5rem'
                  }}>
                    Girls
                  </div>
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem'
                  }}>
                    {sortAgeGroupsNumerically(ageGroups.filter(a => a.startsWith('G'))).map(age => (
                      <button
                        key={age}
                        onClick={() => {
                          handleFilterChange(setSelectedGender, 'Girls');
                          handleFilterChange(setSelectedAgeGroup, age);
                          setSelectedConference('');
                          setShowGenderAgeSheet(false);
                        }}
                        style={{
                          padding: '0.5rem 0.75rem',
                          border: selectedGender === 'Girls' && selectedAgeGroup === age ? '2px solid var(--primary-green)' : '1px solid #ddd',
                          borderRadius: '8px',
                          background: selectedGender === 'Girls' && selectedAgeGroup === age ? '#e8f5e9' : 'white',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          fontWeight: selectedGender === 'Girls' && selectedAgeGroup === age ? '600' : '400',
                          color: selectedGender === 'Girls' && selectedAgeGroup === age ? 'var(--primary-green)' : '#333',
                          textAlign: 'center'
                        }}
                      >
                        {age}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Boys Column */}
                <div style={{ flex: 1 }}>
                  <div style={{
                    padding: '0.5rem 0',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    color: '#888',
                    textTransform: 'uppercase',
                    borderBottom: '1px solid #eee',
                    marginBottom: '0.5rem'
                  }}>
                    Boys
                  </div>
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem'
                  }}>
                    {sortAgeGroupsNumerically(ageGroups.filter(a => a.startsWith('B'))).map(age => (
                      <button
                        key={age}
                        onClick={() => {
                          handleFilterChange(setSelectedGender, 'Boys');
                          handleFilterChange(setSelectedAgeGroup, age);
                          setSelectedConference('');
                          setShowGenderAgeSheet(false);
                        }}
                        style={{
                          padding: '0.5rem 0.75rem',
                          border: selectedGender === 'Boys' && selectedAgeGroup === age ? '2px solid var(--primary-green)' : '1px solid #ddd',
                          borderRadius: '8px',
                          background: selectedGender === 'Boys' && selectedAgeGroup === age ? '#e8f5e9' : 'white',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          fontWeight: selectedGender === 'Boys' && selectedAgeGroup === age ? '600' : '400',
                          color: selectedGender === 'Boys' && selectedAgeGroup === age ? 'var(--primary-green)' : '#333',
                          textAlign: 'center'
                        }}
                      >
                        {age}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ConferenceSimulation;
