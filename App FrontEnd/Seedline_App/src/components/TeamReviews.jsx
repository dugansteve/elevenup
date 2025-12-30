/**
 * TeamReviews.jsx
 * Displays team ratings and reviews with category averages.
 */

import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useUser } from '../context/UserContext';
import { isElevenUpBrand } from '../config/brand';

// Category labels for display
const CATEGORY_LABELS = {
  possession: 'Possession',
  direct_attack: 'Direct Attack',
  passing: 'Passing',
  fast: 'Speed',
  shooting: 'Shooting',
  footwork: 'Footwork',
  physical: 'Physical',
  coaching: 'Coaching',
  allstar_players: 'All Stars',
  player_sportsmanship: 'Player Sportsmanship',
  parent_sportsmanship: 'Parent Sportsmanship',
  strong_defense: 'Defense',
  strong_midfield: 'Midfield',
  strong_offense: 'Offense'
};

// Category groups for organized display
const CATEGORY_GROUPS = {
  'Play Style': ['possession', 'direct_attack', 'passing', 'fast'],
  'Technical': ['shooting', 'footwork', 'physical'],
  'Strengths': ['strong_defense', 'strong_midfield', 'strong_offense'],
  'Culture': ['coaching', 'allstar_players', 'player_sportsmanship', 'parent_sportsmanship']
};

function RatingBar({ label, value, compact = false }) {
  if (value === null || value === undefined) return null;

  const getColor = (val) => {
    if (val >= 4) return '#10b981';
    if (val >= 3) return '#f59e0b';
    return '#ef4444';
  };

  if (compact) {
    return (
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        background: '#f3f4f6',
        borderRadius: 4,
        fontSize: 12
      }}>
        <span style={{ color: '#6b7280' }}>{label}:</span>
        <span style={{ color: getColor(value), fontWeight: 500 }}>{value.toFixed(1)}</span>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      marginBottom: 6
    }}>
      <span style={{ width: 100, fontSize: 13, color: '#4b5563' }}>{label}</span>
      <div style={{
        flex: 1,
        height: 8,
        background: '#e5e7eb',
        borderRadius: 4,
        maxWidth: 80,
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${(value / 5) * 100}%`,
          height: '100%',
          background: getColor(value),
          borderRadius: 4,
          transition: 'width 0.3s ease'
        }} />
      </div>
      <span style={{
        fontSize: 13,
        fontWeight: 500,
        width: 28,
        color: getColor(value)
      }}>
        {value.toFixed(1)}
      </span>
    </div>
  );
}

function RelationshipBadge({ relationship }) {
  const styles = {
    my_team: { bg: '#dbeafe', color: '#1d4ed8', label: 'My Team' },
    followed: { bg: '#f3e8ff', color: '#7c3aed', label: 'Following' },
    neither: { bg: '#f3f4f6', color: '#6b7280', label: 'Observer' }
  };

  const style = styles[relationship] || styles.neither;

  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: 12,
      fontSize: 11,
      fontWeight: 500,
      background: style.bg,
      color: style.color
    }}>
      {style.label}
    </span>
  );
}

function StarDisplay({ value }) {
  return (
    <span style={{ color: isElevenUpBrand ? '#76FF03' : '#f59e0b', letterSpacing: -1 }}>
      {'\u2605'.repeat(value)}
      {'\u2606'.repeat(5 - value)}
    </span>
  );
}

function formatDate(dateStr) {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  } catch {
    return dateStr;
  }
}

export default function TeamReviews({ teamId, teamName, onAddRating }) {
  const { user, isPaid } = useUser();
  const [data, setData] = useState({ averages: {}, ratings: [], total_ratings: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    loadRatings();
  }, [teamId]);

  const loadRatings = async () => {
    // For now, just show empty state - ratings require backend server
    // TODO: Enable API call when backend is consistently running
    setData({ averages: {}, ratings: [], total_ratings: 0 });
    setLoading(false);
  };

  const handleDelete = async (ratingId) => {
    if (!window.confirm('Are you sure you want to delete your review?')) {
      return;
    }

    setDeletingId(ratingId);
    try {
      const result = await api.delete(`/api/v1/ratings/${ratingId}`);
      if (result.success) {
        // Reload ratings after delete
        await loadRatings();
      } else {
        alert(result.error || 'Failed to delete review');
      }
    } catch (err) {
      alert(err.message || 'Failed to delete review');
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div style={{
        padding: 40,
        textAlign: 'center',
        color: '#6b7280'
      }}>
        <div style={{
          display: 'inline-block',
          width: 24,
          height: 24,
          border: '3px solid #e5e7eb',
          borderTopColor: '#2563eb',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
        <div style={{ marginTop: 12 }}>Loading reviews...</div>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: 20,
        textAlign: 'center',
        color: '#dc2626'
      }}>
        <div style={{ marginBottom: 12 }}>Error: {error}</div>
        <button
          onClick={loadRatings}
          style={{
            padding: '8px 16px',
            background: '#f3f4f6',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer'
          }}
        >
          Try Again
        </button>
      </div>
    );
  }

  const hasAverages = data.averages && Object.keys(data.averages).length > 0 &&
    Object.values(data.averages).some(v => v !== null && v !== undefined);

  return (
    <div style={{ padding: 16 }}>
      {/* Add Rating Button */}
      {isPaid && (
        <div style={{ marginBottom: 20 }}>
          <button
            onClick={onAddRating}
            style={{
              padding: '10px 20px',
              background: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}
          >
            <span style={{ fontSize: 18 }}>+</span>
            Add Your Rating
          </button>
        </div>
      )}

      {/* Summary averages */}
      {hasAverages && (
        <div style={{
          marginBottom: 24,
          padding: 16,
          background: '#f9fafb',
          borderRadius: 8,
          border: '1px solid #e5e7eb'
        }}>
          <h4 style={{
            margin: '0 0 16px 0',
            fontSize: 15,
            fontWeight: 600,
            color: '#374151'
          }}>
            Rating Averages
            <span style={{
              fontWeight: 400,
              color: '#6b7280',
              marginLeft: 8,
              fontSize: 13
            }}>
              ({data.total_ratings} review{data.total_ratings !== 1 ? 's' : ''})
            </span>
          </h4>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 16
          }}>
            {Object.entries(CATEGORY_GROUPS).map(([groupName, categories]) => {
              const hasGroupRatings = categories.some(cat => data.averages[cat] !== null);
              if (!hasGroupRatings) return null;

              return (
                <div key={groupName}>
                  <div style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: '#9ca3af',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 8
                  }}>
                    {groupName}
                  </div>
                  {categories.map(cat => (
                    <RatingBar
                      key={cat}
                      label={CATEGORY_LABELS[cat]}
                      value={data.averages[cat]}
                    />
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Individual reviews */}
      <div>
        <h4 style={{
          margin: '0 0 16px 0',
          fontSize: 15,
          fontWeight: 600,
          color: '#374151'
        }}>
          Reviews
        </h4>

        {(!data.ratings || data.ratings.length === 0) ? (
          <div style={{
            padding: 40,
            textAlign: 'center',
            color: '#6b7280',
            background: '#f9fafb',
            borderRadius: 8,
            border: '1px dashed #d1d5db'
          }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>&#9733;</div>
            <div style={{ marginBottom: 8 }}>No reviews yet</div>
            {isPaid ? (
              <button
                onClick={onAddRating}
                style={{
                  padding: '8px 16px',
                  background: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontSize: 13
                }}
              >
                Be the first to rate this team
              </button>
            ) : (
              <div style={{ fontSize: 13 }}>
                Pro accounts can submit ratings
              </div>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {data.ratings.map(rating => (
              <div
                key={rating.id}
                style={{
                  padding: 16,
                  background: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: 8
                }}
              >
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 12
                }}>
                  <RelationshipBadge relationship={rating.relationship} />
                  <span style={{ fontSize: 12, color: '#9ca3af' }}>
                    {formatDate(rating.created_at)}
                  </span>
                </div>

                <p style={{
                  margin: '0 0 12px 0',
                  lineHeight: 1.6,
                  color: '#374151',
                  fontSize: 14
                }}>
                  {rating.comment}
                </p>

                {rating.ratings && Object.keys(rating.ratings).length > 0 && (
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 6,
                    paddingTop: 12,
                    borderTop: '1px solid #f3f4f6'
                  }}>
                    {Object.entries(rating.ratings).map(([key, value]) => (
                      <div
                        key={key}
                        style={{
                          fontSize: 12,
                          padding: '3px 8px',
                          background: '#f3f4f6',
                          borderRadius: 4,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4
                        }}
                      >
                        <span style={{ color: '#6b7280' }}>{CATEGORY_LABELS[key]}:</span>
                        <StarDisplay value={value} />
                      </div>
                    ))}
                  </div>
                )}

                {/* Delete button for own reviews - would need user ID matching */}
                {/* For now, we'll skip this since we don't expose user_id in the response */}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
