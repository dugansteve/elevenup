// SubmitGameForm.jsx
// Component for submitting missing games on team pages

import { useState, useMemo } from 'react';
import { EVENT_TYPES, userGameHelpers } from '../data/sampleData';
import { useRankingsData } from '../data/useRankingsData';
import { validateGameUrl, getValidationDisplay } from '../data/urlValidatorService';

export default function SubmitGameForm({ team, onSubmit, onCancel }) {
  const { teamsData, ageGroups, leagues } = useRankingsData();
  
  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchAgeGroup, setSearchAgeGroup] = useState(team.ageGroup);
  const [searchLeague, setSearchLeague] = useState('');
  const [selectedOpponent, setSelectedOpponent] = useState(null);
  
  // Form state
  const [gameDate, setGameDate] = useState('');
  const [teamScore, setTeamScore] = useState('');
  const [opponentScore, setOpponentScore] = useState('');
  const [location, setLocation] = useState('');
  const [scoreUrl, setScoreUrl] = useState('');
  const [eventType, setEventType] = useState('league_play');
  const [otherEventType, setOtherEventType] = useState('');
  
  // UI state
  const [showSearch, setShowSearch] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [validationStatus, setValidationStatus] = useState(null);
  const [isValidating, setIsValidating] = useState(false);

  // Filter teams for search (exclude current team)
  const filteredTeams = useMemo(() => {
    if (!searchQuery && !searchLeague) return [];
    
    return teamsData.filter(t => {
      // Exclude the current team
      if (t.id === team.id) return false;
      
      // Filter by age group (must match)
      if (t.ageGroup !== searchAgeGroup) return false;
      
      // Filter by league if selected
      if (searchLeague && t.league !== searchLeague) return false;
      
      // Filter by search query (name)
      if (searchQuery) {
        const queryLower = searchQuery.toLowerCase();
        const nameMatch = t.name.toLowerCase().includes(queryLower);
        const clubMatch = t.club?.toLowerCase().includes(queryLower);
        if (!nameMatch && !clubMatch) return false;
      }
      
      return true;
    }).slice(0, 20); // Limit to 20 results
  }, [teamsData, searchQuery, searchAgeGroup, searchLeague, team.id]);

  // Handle opponent selection
  const handleSelectOpponent = (opponent) => {
    setSelectedOpponent(opponent);
    setShowSearch(false);
    setSearchQuery('');
  };

  // Clear opponent selection
  const handleClearOpponent = () => {
    setSelectedOpponent(null);
    setShowSearch(true);
  };

  // Validate form
  const isFormValid = () => {
    if (!selectedOpponent) return false;
    if (!gameDate) return false;
    if (teamScore === '' || opponentScore === '') return false;
    if (parseInt(teamScore) < 0 || parseInt(opponentScore) < 0) return false;
    if (eventType === 'other' && !otherEventType.trim()) return false;
    return true;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!isFormValid()) {
      setError('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setValidationStatus(null);

    try {
      // Check for duplicate
      const duplicate = userGameHelpers.checkDuplicate(
        team.name,
        selectedOpponent.name,
        gameDate,
        team.ageGroup
      );

      if (duplicate) {
        setError('This game has already been submitted');
        setIsSubmitting(false);
        return;
      }

      // Prepare game data
      const gameData = {
        homeTeam: team.name,
        awayTeam: selectedOpponent.name,
        homeScore: parseInt(teamScore),
        awayScore: parseInt(opponentScore),
        date: gameDate,
        ageGroup: team.ageGroup,
        league: team.league,
        location: location.trim() || null,
        scoreUrl: scoreUrl.trim() || null,
        eventType: eventType === 'other' ? otherEventType.trim() : eventType,
        eventTypeName: eventType === 'other' 
          ? otherEventType.trim() 
          : EVENT_TYPES.find(e => e.id === eventType)?.name || eventType,
      };

      // Submit the game
      const newGame = userGameHelpers.submitGame(gameData);
      
      // If URL provided, try to validate it
      if (scoreUrl.trim()) {
        setIsValidating(true);
        setValidationStatus({ message: 'AI is verifying the URL...' });
        
        try {
          const validationResult = await validateGameUrl(scoreUrl.trim(), gameData);
          userGameHelpers.saveValidationResult(newGame.id, validationResult);
          setValidationStatus(validationResult);
        } catch (validationError) {
          console.error('URL validation error:', validationError);
          setValidationStatus({ 
            message: 'URL validation skipped. Community verification will be used.',
            serverOffline: true 
          });
        } finally {
          setIsValidating(false);
        }
      }
      
      setSuccess(true);
      
      // Notify parent
      if (onSubmit) {
        onSubmit(newGame);
      }

      // Reset form after short delay
      setTimeout(() => {
        setSelectedOpponent(null);
        setShowSearch(true);
        setGameDate('');
        setTeamScore('');
        setOpponentScore('');
        setLocation('');
        setScoreUrl('');
        setEventType('league_play');
        setOtherEventType('');
        setSuccess(false);
        setValidationStatus(null);
      }, 3000);

    } catch (err) {
      setError('Failed to submit game. Please try again.');
      console.error('Submit game error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render success message
  if (success) {
    const display = validationStatus ? getValidationDisplay(validationStatus) : null;
    
    return (
      <div style={{
        padding: '2rem',
        textAlign: 'center',
        background: '#e8f5e9',
        borderRadius: '12px',
        border: '1px solid #a5d6a7'
      }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✅</div>
        <h3 style={{ color: '#2e7d32', marginBottom: '0.5rem' }}>Game Submitted!</h3>
        <p style={{ color: '#666' }}>
          Your game has been submitted and is pending verification.
        </p>
        
        {/* Show validation status if URL was provided */}
        {validationStatus && (
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem',
            background: display?.bg || '#f5f5f5',
            borderRadius: '8px',
            fontSize: '0.9rem'
          }}>
            <div style={{ 
              fontWeight: '600', 
              color: display?.color || '#666',
              marginBottom: '0.25rem'
            }}>
              {display?.icon} {display?.text}
            </div>
            {validationStatus.message && (
              <div style={{ color: '#666', fontSize: '0.85rem' }}>
                {validationStatus.message}
              </div>
            )}
          </div>
        )}
        
        {isValidating && (
          <div style={{ marginTop: '1rem', color: '#666' }}>
            🤖 AI is verifying the URL...
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ padding: '1rem' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '1.5rem'
      }}>
        <h3 style={{ 
          fontSize: '1.1rem', 
          fontWeight: '600', 
          color: 'var(--primary-green)',
          margin: 0
        }}>
          📝 Report Missing Game
        </h3>
        {onCancel && (
          <button
            onClick={onCancel}
            style={{
              background: 'none',
              border: 'none',
              color: '#666',
              cursor: 'pointer',
              fontSize: '1.5rem',
              padding: '0.25rem'
            }}
          >
            ×
          </button>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div style={{
          padding: '0.75rem 1rem',
          background: '#ffebee',
          color: '#c62828',
          borderRadius: '8px',
          marginBottom: '1rem',
          fontSize: '0.9rem'
        }}>
          {error}
        </div>
      )}

      {/* Step 1: Select opponent */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ 
          display: 'block', 
          fontWeight: '600', 
          marginBottom: '0.5rem',
          color: '#333'
        }}>
          1. Select Opponent Team *
        </label>

        {selectedOpponent ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.75rem 1rem',
            background: '#e3f2fd',
            borderRadius: '8px',
            border: '1px solid #90caf9'
          }}>
            <div>
              <div style={{ fontWeight: '600' }}>{selectedOpponent.name}</div>
              <div style={{ fontSize: '0.85rem', color: '#666' }}>
                {selectedOpponent.league} • {selectedOpponent.ageGroup}
              </div>
            </div>
            <button
              onClick={handleClearOpponent}
              style={{
                background: 'none',
                border: 'none',
                color: '#1976d2',
                cursor: 'pointer',
                fontSize: '0.9rem'
              }}
            >
              Change
            </button>
          </div>
        ) : (
          <div>
            {/* Search filters */}
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: '1fr 1fr', 
              gap: '0.5rem',
              marginBottom: '0.5rem'
            }}>
              <select
                value={searchAgeGroup}
                onChange={(e) => setSearchAgeGroup(e.target.value)}
                style={{
                  padding: '0.5rem',
                  borderRadius: '6px',
                  border: '1px solid #ddd',
                  fontSize: '0.9rem'
                }}
              >
                {ageGroups.map(ag => (
                  <option key={ag} value={ag}>{ag}</option>
                ))}
              </select>
              <select
                value={searchLeague}
                onChange={(e) => setSearchLeague(e.target.value)}
                style={{
                  padding: '0.5rem',
                  borderRadius: '6px',
                  border: '1px solid #ddd',
                  fontSize: '0.9rem'
                }}
              >
                <option value="">All Leagues</option>
                {leagues.map(lg => (
                  <option key={lg} value={lg}>{lg}</option>
                ))}
              </select>
            </div>

            {/* Search input */}
            <input
              type="text"
              placeholder="Search team by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid #ddd',
                fontSize: '0.95rem',
                boxSizing: 'border-box'
              }}
            />

            {/* Search results */}
            {filteredTeams.length > 0 && (
              <div style={{
                maxHeight: '200px',
                overflowY: 'auto',
                border: '1px solid #ddd',
                borderRadius: '8px',
                marginTop: '0.5rem'
              }}>
                {filteredTeams.map(t => (
                  <div
                    key={t.id}
                    onClick={() => handleSelectOpponent(t)}
                    style={{
                      padding: '0.75rem 1rem',
                      cursor: 'pointer',
                      borderBottom: '1px solid #eee',
                      transition: 'background 0.2s'
                    }}
                    onMouseEnter={(e) => e.target.style.background = '#f5f5f5'}
                    onMouseLeave={(e) => e.target.style.background = 'transparent'}
                  >
                    <div style={{ fontWeight: '500' }}>{t.name} {t.ageGroup}</div>
                    <div style={{ fontSize: '0.8rem', color: '#888' }}>
                      {t.league} • Rank #{t.rank}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {searchQuery && filteredTeams.length === 0 && (
              <div style={{
                padding: '1rem',
                textAlign: 'center',
                color: '#888',
                fontSize: '0.9rem'
              }}>
                No teams found matching "{searchQuery}"
              </div>
            )}
          </div>
        )}
      </div>

      {/* Step 2: Game details form */}
      {selectedOpponent && (
        <form onSubmit={handleSubmit}>
          {/* Date */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontWeight: '600', 
              marginBottom: '0.5rem',
              color: '#333'
            }}>
              2. Game Date *
            </label>
            <input
              type="date"
              value={gameDate}
              onChange={(e) => setGameDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              required
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid #ddd',
                fontSize: '0.95rem',
                boxSizing: 'border-box'
              }}
            />
          </div>

          {/* Scores */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontWeight: '600', 
              marginBottom: '0.5rem',
              color: '#333'
            }}>
              3. Final Score *
            </label>
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: '1fr auto 1fr', 
              gap: '0.5rem',
              alignItems: 'center'
            }}>
              <div>
                <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                  {team.name} {team.ageGroup}
                </div>
                <input
                  type="number"
                  min="0"
                  max="99"
                  value={teamScore}
                  onChange={(e) => setTeamScore(e.target.value)}
                  placeholder="0"
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid #ddd',
                    fontSize: '1.25rem',
                    textAlign: 'center',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
              <div style={{ 
                fontSize: '1.25rem', 
                fontWeight: 'bold',
                color: '#666',
                padding: '0 0.5rem'
              }}>
                -
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                  {selectedOpponent.name}
                </div>
                <input
                  type="number"
                  min="0"
                  max="99"
                  value={opponentScore}
                  onChange={(e) => setOpponentScore(e.target.value)}
                  placeholder="0"
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '8px',
                    border: '1px solid #ddd',
                    fontSize: '1.25rem',
                    textAlign: 'center',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </div>
          </div>

          {/* Event Type */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontWeight: '600', 
              marginBottom: '0.5rem',
              color: '#333'
            }}>
              4. Event Type *
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid #ddd',
                fontSize: '0.95rem',
                boxSizing: 'border-box'
              }}
            >
              {EVENT_TYPES.map(et => (
                <option key={et.id} value={et.id}>{et.name}</option>
              ))}
            </select>
            {eventType === 'other' && (
              <input
                type="text"
                placeholder="Enter event type..."
                value={otherEventType}
                onChange={(e) => setOtherEventType(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  fontSize: '0.95rem',
                  marginTop: '0.5rem',
                  boxSizing: 'border-box'
                }}
              />
            )}
          </div>

          {/* Location (optional) */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontWeight: '600', 
              marginBottom: '0.5rem',
              color: '#333'
            }}>
              5. Location <span style={{ fontWeight: 'normal', color: '#888' }}>(optional)</span>
            </label>
            <input
              type="text"
              placeholder="e.g., Main Stadium, City Park"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid #ddd',
                fontSize: '0.95rem',
                boxSizing: 'border-box'
              }}
            />
          </div>

          {/* Score URL (optional) */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ 
              display: 'block', 
              fontWeight: '600', 
              marginBottom: '0.5rem',
              color: '#333'
            }}>
              6. Score Verification URL <span style={{ fontWeight: 'normal', color: '#888' }}>(optional)</span>
            </label>
            <input
              type="url"
              placeholder="https://..."
              value={scoreUrl}
              onChange={(e) => setScoreUrl(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid #ddd',
                fontSize: '0.95rem',
                boxSizing: 'border-box'
              }}
            />
            <p style={{ 
              fontSize: '0.8rem', 
              color: '#666', 
              marginTop: '0.5rem',
              lineHeight: '1.4'
            }}>
              💡 Providing a URL with the score (league website, social media post, etc.) 
              helps verify your submission faster through automatic verification.
            </p>
          </div>

          {/* Submit button */}
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                style={{
                  flex: 1,
                  padding: '0.875rem',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  background: '#fff',
                  color: '#666',
                  fontSize: '1rem',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
            )}
            <button
              type="submit"
              disabled={!isFormValid() || isSubmitting}
              style={{
                flex: 2,
                padding: '0.875rem',
                borderRadius: '8px',
                border: 'none',
                background: isFormValid() ? 'var(--primary-green)' : '#ccc',
                color: '#fff',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: isFormValid() && !isSubmitting ? 'pointer' : 'not-allowed',
                opacity: isSubmitting ? 0.7 : 1
              }}
            >
              {isSubmitting ? 'Submitting...' : 'Submit Game'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
