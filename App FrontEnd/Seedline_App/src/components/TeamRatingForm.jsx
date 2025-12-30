/**
 * TeamRatingForm.jsx
 * Component for submitting team ratings with star ratings and comments.
 * Comments are moderated by Claude AI before being published.
 */

import { useState } from 'react';
import { useUser } from '../context/UserContext';
import { api } from '../services/api';
import { isElevenUpBrand } from '../config/brand';

// Rating categories grouped by type
const RATING_CATEGORIES = {
  'Play Style': [
    { id: 'possession', label: 'Possession' },
    { id: 'direct_attack', label: 'Direct Attack' },
    { id: 'passing', label: 'Passing' },
    { id: 'fast', label: 'Fast' },
  ],
  'Technical': [
    { id: 'shooting', label: 'Shooting' },
    { id: 'footwork', label: 'Footwork' },
    { id: 'physical', label: 'Physical' },
  ],
  'Team Strengths': [
    { id: 'strong_defense', label: 'Strong Defense' },
    { id: 'strong_midfield', label: 'Strong Midfield' },
    { id: 'strong_offense', label: 'Strong Offense' },
  ],
  'Culture': [
    { id: 'coaching', label: 'Coaching' },
    { id: 'allstar_players', label: 'All Star Player(s)' },
    { id: 'player_sportsmanship', label: 'Player Sportsmanship' },
    { id: 'parent_sportsmanship', label: 'Parent Sportsmanship' },
  ]
};

function StarRating({ value, onChange, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
      <span style={{ width: 140, fontSize: 13, color: '#4b5563' }}>{label}</span>
      <div style={{ display: 'flex', gap: 2 }}>
        {[1, 2, 3, 4, 5].map(star => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(value === star ? null : star)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 18,
              color: value >= star ? (isElevenUpBrand ? '#76FF03' : '#f59e0b') : '#d1d5db',
              padding: '0 2px',
              transition: 'transform 0.1s'
            }}
            onMouseEnter={(e) => e.target.style.transform = 'scale(1.2)'}
            onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
          >
            {value >= star ? '\u2605' : '\u2606'}
          </button>
        ))}
        {value && (
          <button
            type="button"
            onClick={() => onChange(null)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 11,
              color: '#9ca3af',
              marginLeft: 6,
              padding: '2px 4px'
            }}
          >
            clear
          </button>
        )}
      </div>
    </div>
  );
}

export default function TeamRatingForm({ team, onSubmit, onCancel }) {
  const { user, isPaid, isInMyTeams, isFollowing } = useUser();
  const [ratings, setRatings] = useState({});
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [moderationError, setModerationError] = useState(null);

  // Determine relationship to team
  const getRelationship = () => {
    if (isInMyTeams(team)) return 'my_team';
    if (isFollowing(team)) return 'followed';
    return 'neither';
  };

  const handleRatingChange = (categoryId, value) => {
    setRatings(prev => ({
      ...prev,
      [categoryId]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setModerationError(null);

    if (!comment.trim() || comment.length < 10) {
      setError('Please write a comment about the team (at least 10 characters)');
      return;
    }

    if (comment.length > 1000) {
      setError('Comment must be less than 1000 characters');
      return;
    }

    setIsSubmitting(true);

    try {
      // Add timeout to prevent long waits if backend isn't running
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      const fetchResponse = await fetch('/api/v1/ratings/submit', {
        method: 'POST',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_id: team.id,
          team_name: team.name,
          team_age_group: team.ageGroup,
          team_league: team.league,
          relationship: getRelationship(),
          comment: comment.trim(),
          ratings,
          session_id: api.sessionId
        })
      });
      clearTimeout(timeoutId);

      if (!fetchResponse.ok) {
        if (fetchResponse.status === 404) {
          setError('Rating service not available. Please ensure the backend server is running.');
        } else {
          setError(`Server error: ${fetchResponse.status}`);
        }
        return;
      }

      const response = await fetchResponse.json();

      if (response.success) {
        onSubmit?.(response);
      } else if (response.code === 'MODERATION_REJECTED') {
        setModerationError(response.moderation_reason);
      } else {
        setError(response.error || 'Failed to submit rating');
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out. Please ensure the backend server is running on port 5050.');
      } else {
        setError(err.message || 'Network error - please try again');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Non-paid users see upgrade message
  if (!isPaid) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>&#9733;</div>
        <h3 style={{ marginBottom: 8 }}>Pro Feature</h3>
        <p style={{ color: '#6b7280', marginBottom: 16 }}>
          Team ratings are available for Pro accounts.
        </p>
        <button
          onClick={onCancel}
          style={{
            padding: '8px 20px',
            background: '#f3f4f6',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 14
          }}
        >
          Close
        </button>
      </div>
    );
  }

  const relationship = getRelationship();
  const relationshipLabel = {
    my_team: 'My Team',
    followed: 'Following',
    neither: 'Neutral Observer'
  }[relationship];

  const ratedCount = Object.values(ratings).filter(v => v !== null && v !== undefined).length;

  return (
    <form onSubmit={handleSubmit} style={{ padding: 20 }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
        paddingBottom: 12,
        borderBottom: '1px solid #e5e7eb'
      }}>
        <h3 style={{ margin: 0, fontSize: 18 }}>Rate {team.name}</h3>
        <button
          type="button"
          onClick={onCancel}
          style={{
            background: 'none',
            border: 'none',
            fontSize: 20,
            cursor: 'pointer',
            color: '#9ca3af',
            padding: 4
          }}
        >
          &times;
        </button>
      </div>

      {/* Relationship indicator */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        marginBottom: 20,
        padding: '8px 12px',
        background: '#f9fafb',
        borderRadius: 6,
        fontSize: 13
      }}>
        <span style={{ color: '#6b7280' }}>Your relationship:</span>
        <span style={{
          display: 'inline-block',
          padding: '2px 10px',
          borderRadius: 12,
          fontSize: 12,
          fontWeight: 500,
          background: relationship === 'my_team' ? '#dbeafe' :
                     relationship === 'followed' ? '#f3e8ff' : '#f3f4f6',
          color: relationship === 'my_team' ? '#1d4ed8' :
                 relationship === 'followed' ? '#7c3aed' : '#6b7280'
        }}>
          {relationshipLabel}
        </span>
      </div>

      {/* Rating categories */}
      <div style={{ marginBottom: 20 }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12
        }}>
          <span style={{ fontSize: 14, fontWeight: 500, color: '#374151' }}>
            Rate Categories (optional)
          </span>
          <span style={{ fontSize: 12, color: '#9ca3af' }}>
            {ratedCount} of 14 rated
          </span>
        </div>

        {Object.entries(RATING_CATEGORIES).map(([groupName, categories]) => (
          <div key={groupName} style={{ marginBottom: 16 }}>
            <div style={{
              fontSize: 12,
              fontWeight: 600,
              color: '#6b7280',
              marginBottom: 6,
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              {groupName}
            </div>
            {categories.map(cat => (
              <StarRating
                key={cat.id}
                label={cat.label}
                value={ratings[cat.id]}
                onChange={(value) => handleRatingChange(cat.id, value)}
              />
            ))}
          </div>
        ))}
      </div>

      {/* Comment (required) */}
      <div style={{ marginBottom: 20 }}>
        <label style={{
          display: 'block',
          marginBottom: 6,
          fontWeight: 500,
          fontSize: 14
        }}>
          Comment about team style of play *
        </label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Describe how this team plays, their strengths, coaching style, etc. Be constructive and respectful."
          style={{
            width: '100%',
            minHeight: 100,
            padding: 12,
            borderRadius: 6,
            border: '1px solid #d1d5db',
            resize: 'vertical',
            fontSize: 14,
            fontFamily: 'inherit',
            boxSizing: 'border-box'
          }}
          maxLength={1000}
        />
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 12,
          color: comment.length < 10 ? '#ef4444' : '#9ca3af',
          marginTop: 4
        }}>
          <span>{comment.length < 10 ? `${10 - comment.length} more characters needed` : 'Comment will be reviewed before posting'}</span>
          <span>{comment.length}/1000</span>
        </div>
      </div>

      {/* Errors */}
      {error && (
        <div style={{
          padding: 12,
          background: '#fef2f2',
          color: '#dc2626',
          borderRadius: 6,
          marginBottom: 16,
          fontSize: 14
        }}>
          {error}
        </div>
      )}

      {moderationError && (
        <div style={{
          padding: 12,
          background: '#fff7ed',
          borderRadius: 6,
          marginBottom: 16,
          border: '1px solid #fed7aa'
        }}>
          <div style={{ fontWeight: 500, color: '#c2410c', marginBottom: 4, fontSize: 14 }}>
            Comment not approved
          </div>
          <div style={{ color: '#9a3412', fontSize: 13 }}>
            {moderationError}
          </div>
          <div style={{ color: '#78350f', fontSize: 12, marginTop: 8 }}>
            Please edit your comment and try again.
          </div>
        </div>
      )}

      {/* Buttons */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          style={{
            padding: '10px 20px',
            background: '#f3f4f6',
            border: 'none',
            borderRadius: 6,
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            fontSize: 14,
            fontWeight: 500
          }}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting || comment.length < 10}
          style={{
            padding: '10px 24px',
            background: isSubmitting || comment.length < 10 ? '#9ca3af' : '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: 6,
            cursor: isSubmitting || comment.length < 10 ? 'not-allowed' : 'pointer',
            fontSize: 14,
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}
        >
          {isSubmitting ? (
            <>
              <span style={{
                display: 'inline-block',
                width: 14,
                height: 14,
                border: '2px solid white',
                borderTopColor: 'transparent',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
              Submitting...
            </>
          ) : (
            'Submit Rating'
          )}
        </button>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </form>
  );
}
