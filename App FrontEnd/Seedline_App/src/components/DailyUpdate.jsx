import { useState, useEffect } from 'react';
import { useUser } from '../context/UserContext';
import { dailyUpdateHelpers } from '../data/sampleData';

// Generate team key for storage
const getTeamKey = (team) => {
  return `${team.name?.toLowerCase() || ''}_${team.ageGroup?.toLowerCase() || ''}`;
};

// Format date for display
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
};

// Helper to normalize team name for comparison
const normalizeTeamName = (name) => {
  if (!name) return '';
  return name.toLowerCase().replace(/\s+/g, ' ').trim();
};

// Helper to get game result and details from raw game data
const processGame = (game, teamName) => {
  const normalizedTeam = normalizeTeamName(teamName);
  const normalizedHome = normalizeTeamName(game.homeTeam);
  const normalizedAway = normalizeTeamName(game.awayTeam);

  const isHome = normalizedHome === normalizedTeam || normalizedHome.includes(normalizedTeam) || normalizedTeam.includes(normalizedHome);
  const opponent = isHome ? game.awayTeam : game.homeTeam;

  const teamScore = isHome ? game.homeScore : game.awayScore;
  const oppScore = isHome ? game.awayScore : game.homeScore;

  let result = 'D';
  if (teamScore > oppScore) result = 'W';
  else if (teamScore < oppScore) result = 'L';

  return { isHome, opponent, teamScore, oppScore, result };
};

// Generate update content based on team data
const generateUpdateContent = (team, teamGames) => {
  const sections = [];

  // Recent results section
  const recentGames = teamGames?.past?.slice(0, 5) || [];
  if (recentGames.length > 0) {
    const processedGames = recentGames.map(g => ({ ...g, ...processGame(g, team.name) }));
    const wins = processedGames.filter(g => g.result === 'W').length;
    const losses = processedGames.filter(g => g.result === 'L').length;
    const draws = processedGames.filter(g => g.result === 'D').length;

    let resultSummary = `**Recent Form:** ${wins}W-${losses}L-${draws}D in the last ${recentGames.length} games.`;

    const lastGame = processedGames[0];
    if (lastGame && lastGame.teamScore !== null && lastGame.oppScore !== null) {
      const resultWord = lastGame.result === 'W' ? 'won' : lastGame.result === 'L' ? 'lost' : 'drew';
      resultSummary += ` Most recently ${resultWord} ${lastGame.teamScore}-${lastGame.oppScore} ${lastGame.isHome ? 'vs' : 'at'} ${lastGame.opponent}.`;
    }
    sections.push(resultSummary);
  }

  // Rankings impact - always show if we have basic team data
  if (team.nationalRank || team.powerScore) {
    let rankingNote = `**Current Standing:** `;
    if (team.nationalRank) {
      rankingNote += `Ranked #${team.nationalRank} nationally`;
      if (team.powerScore) {
        rankingNote += ` with a power score of ${team.powerScore?.toFixed(0)}`;
      }
      rankingNote += '.';
    } else if (team.powerScore) {
      rankingNote += `Power score of ${team.powerScore?.toFixed(0)}.`;
    }

    if (team.wins !== undefined || team.losses !== undefined) {
      rankingNote += ` Season record: ${team.wins || 0}-${team.losses || 0}-${team.draws || 0}.`;
    }
    if (team.sos) {
      rankingNote += ` Strength of schedule: ${(team.sos * 100).toFixed(0)}%.`;
    }
    sections.push(rankingNote);
  }

  // Upcoming games
  const upcomingGames = teamGames?.upcoming?.slice(0, 3) || [];
  if (upcomingGames.length > 0) {
    let upcomingNote = `**Coming Up:** `;
    const gameDescs = upcomingGames.map(g => {
      const { isHome, opponent } = processGame(g, team.name);
      const date = new Date(g.date);
      const dateStr = !isNaN(date.getTime())
        ? date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        : 'TBD';
      return `${dateStr} ${isHome ? 'vs' : '@'} ${opponent}`;
    });
    upcomingNote += gameDescs.join(', ') + '.';
    sections.push(upcomingNote);
  }

  // Big wins / notable results
  if (team.bigWins > 0) {
    sections.push(`**Notable:** ${team.bigWins} big win${team.bigWins > 1 ? 's' : ''} this season (3+ goal victories against quality opponents).`);
  }

  // Goal differential insight
  if (team.goalsFor !== undefined || team.goalsAgainst !== undefined || team.goalDiff !== undefined) {
    const gf = team.goalsFor || 0;
    const ga = team.goalsAgainst || 0;
    const diff = team.goalDiff !== undefined ? team.goalDiff : (gf - ga);
    const diffSign = diff > 0 ? '+' : '';
    sections.push(`**Attack & Defense:** ${gf} goals scored, ${ga} conceded (${diffSign}${diff} differential).`);
  }

  // League context
  if (team.league) {
    let leagueNote = `**League:** Competing in ${team.league}`;
    if (team.ageGroup) {
      leagueNote += ` for the ${team.ageGroup} age group`;
    }
    if (team.state) {
      leagueNote += ` (${team.state})`;
    }
    leagueNote += '.';
    sections.push(leagueNote);
  }

  // Club info
  if (team.club) {
    sections.push(`**Club:** ${team.club}`);
  }

  // If we still have no sections, add a fallback
  if (sections.length === 0) {
    sections.push(`**${team.name} ${team.ageGroup}** - Check back soon for more detailed insights as more game data becomes available.`);
  }

  // Add a "generated" note
  sections.push(`---\n*This update was generated on ${new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}. Check back tomorrow for fresh insights!*`);

  return sections.join('\n\n');
};

function DailyUpdate({ team, teamGames }) {
  const { isGuest } = useUser();
  const [updates, setUpdates] = useState([]);
  const [selectedUpdate, setSelectedUpdate] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [canGenerate, setCanGenerate] = useState({ allowed: false, reason: '' });

  const teamKey = getTeamKey(team);
  const canUseFeature = !isGuest; // All logged-in users can use this feature

  // Load updates and check generation eligibility
  useEffect(() => {
    const loadedUpdates = dailyUpdateHelpers.getUpdatesForTeam(teamKey);
    setUpdates(loadedUpdates);
    if (loadedUpdates.length > 0) {
      setSelectedUpdate(loadedUpdates[0]);
    }

    const eligibility = dailyUpdateHelpers.canGenerateUpdate(teamKey);
    setCanGenerate(eligibility);
  }, [teamKey]);

  // Handle generate update
  const handleGenerateUpdate = async () => {
    if (!canGenerate.allowed) return;

    setIsGenerating(true);

    // Simulate AI generation delay
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Generate the content
    const content = generateUpdateContent(team, teamGames);

    // Save the update
    const result = dailyUpdateHelpers.saveUpdate(
      teamKey,
      team.name,
      team.ageGroup,
      team.league,
      content
    );

    if (result.success) {
      // Refresh updates
      const loadedUpdates = dailyUpdateHelpers.getUpdatesForTeam(teamKey);
      setUpdates(loadedUpdates);
      setSelectedUpdate(loadedUpdates[0]);
    }

    setIsGenerating(false);
  };

  // Render markdown-like content (basic)
  const renderContent = (content) => {
    if (!content) return null;

    return content.split('\n\n').map((paragraph, idx) => {
      // Bold text
      let text = paragraph.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      // Italic text
      text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
      // Horizontal rule
      if (text.startsWith('---')) {
        return <hr key={idx} style={{ margin: '1rem 0', border: 'none', borderTop: '1px solid #e0e0e0' }} />;
      }

      return (
        <p
          key={idx}
          style={{ marginBottom: '0.75rem', lineHeight: '1.6', color: '#333' }}
          dangerouslySetInnerHTML={{ __html: text }}
        />
      );
    });
  };

  return (
    <div style={{ padding: '0.5rem 0' }}>
      {/* Guest Banner */}
      {!canUseFeature && (
        <div style={{
          background: 'linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%)',
          borderRadius: '12px',
          padding: '1.5rem',
          textAlign: 'center',
          marginBottom: '1rem'
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
            👤
          </div>
          <h3 style={{
            fontSize: '1.1rem',
            fontWeight: '600',
            color: '#333',
            marginBottom: '0.5rem'
          }}>
            Sign In to Use Daily Updates
          </h3>
          <p style={{ color: '#666', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Get AI-powered daily insights about your favorite teams including recent results,
            standings impact, upcoming matchups, and league news.
          </p>
          <div style={{
            display: 'inline-block',
            padding: '0.5rem 1.5rem',
            background: 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)',
            color: 'white',
            borderRadius: '20px',
            fontWeight: '600',
            fontSize: '0.9rem'
          }}>
            Create Free Account
          </div>
        </div>
      )}

      {/* Logged-in user content */}
      {canUseFeature && (
        <>
          {/* Generate Update Button */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '1rem',
            flexWrap: 'wrap',
            gap: '0.5rem'
          }}>
            <div>
              <h3 style={{
                fontSize: '1.1rem',
                fontWeight: '600',
                color: 'var(--primary-green)',
                margin: 0
              }}>
                Daily Update
              </h3>
              <div style={{ fontSize: '0.75rem', color: 'var(--primary-green)', fontWeight: '500', marginTop: '0.25rem' }}>
                Unlimited updates
              </div>
            </div>

            <button
              onClick={handleGenerateUpdate}
              disabled={!canGenerate.allowed || isGenerating}
              style={{
                padding: '0.6rem 1.2rem',
                borderRadius: '8px',
                border: 'none',
                background: canGenerate.allowed
                  ? 'linear-gradient(135deg, var(--primary-green) 0%, #2e7d32 100%)'
                  : '#e0e0e0',
                color: canGenerate.allowed ? 'white' : '#999',
                fontWeight: '600',
                fontSize: '0.85rem',
                cursor: canGenerate.allowed ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              {isGenerating ? (
                <>
                  <span className="loading" style={{ width: '14px', height: '14px' }}></span>
                  Generating...
                </>
              ) : (
                <>Generate Update</>
              )}
            </button>
          </div>

          {/* Reason why can't generate */}
          {!canGenerate.allowed && !isGenerating && (
            <div style={{
              padding: '0.5rem 0.75rem',
              background: '#fff3e0',
              borderRadius: '6px',
              fontSize: '0.8rem',
              color: '#e65100',
              marginBottom: '1rem'
            }}>
              {canGenerate.reason}
            </div>
          )}

          {/* Update History Tabs */}
          {updates.length > 0 && (
            <div style={{
              display: 'flex',
              gap: '0.5rem',
              marginBottom: '1rem',
              overflowX: 'auto',
              paddingBottom: '0.25rem'
            }}>
              {updates.map((update, idx) => (
                <button
                  key={update.id}
                  onClick={() => setSelectedUpdate(update)}
                  style={{
                    padding: '0.4rem 0.8rem',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: selectedUpdate?.id === update.id ? 'var(--primary-green)' : '#ddd',
                    background: selectedUpdate?.id === update.id ? 'var(--primary-green)' : 'white',
                    color: selectedUpdate?.id === update.id ? 'white' : '#666',
                    fontSize: '0.75rem',
                    fontWeight: '500',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {idx === 0 ? 'Latest' : new Date(update.generatedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </button>
              ))}
            </div>
          )}

          {/* Selected Update Content */}
          {selectedUpdate ? (
            <div style={{
              background: '#fafafa',
              borderRadius: '12px',
              padding: '1rem',
              border: '1px solid #e0e0e0'
            }}>
              <div style={{
                fontSize: '0.7rem',
                color: '#888',
                marginBottom: '0.75rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span>Generated {formatDate(selectedUpdate.generatedAt)}</span>
              </div>

              <div>
                {renderContent(selectedUpdate.content)}
              </div>
            </div>
          ) : (
            <div style={{
              textAlign: 'center',
              padding: '2rem',
              color: '#888'
            }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
                {dailyUpdateHelpers.hasUpdateToday(teamKey) ? '...' : '...'}
              </div>
              <p style={{ fontSize: '0.9rem' }}>
                No updates yet. Generate your first daily update to get AI-powered insights about this team!
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default DailyUpdate;
