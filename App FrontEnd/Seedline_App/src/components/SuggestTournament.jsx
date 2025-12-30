import { useState } from 'react';
import { useUser } from '../context/UserContext';
import { currentBrand } from '../config/brand';

// Formspree endpoint - replace with your form ID from https://formspree.io
// Free tier: 50 submissions/month, emails you each submission
const FORMSPREE_ENDPOINT = 'https://formspree.io/f/YOUR_FORM_ID';

// Local storage key for tracking submissions (optional backup) - brand-specific
const SUGGESTIONS_KEY = currentBrand.suggestionsKey;

// Get all suggestions from localStorage (backup)
export function getSuggestions() {
  try {
    const data = localStorage.getItem(SUGGESTIONS_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

// Save a suggestion locally as backup
function saveSuggestionLocally(suggestion) {
  const suggestions = getSuggestions();
  suggestions.push(suggestion);
  localStorage.setItem(SUGGESTIONS_KEY, JSON.stringify(suggestions));
}

// Export suggestions as JSON (backup method)
export function exportSuggestionsJSON() {
  const suggestions = getSuggestions();
  if (suggestions.length === 0) return;

  const dataStr = JSON.stringify({
    suggestions,
    exported_at: new Date().toISOString(),
    count: suggestions.length
  }, null, 2);

  const blob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `tournament_suggestions_${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// US States for dropdown
const US_STATES = [
  { code: '', name: 'Select State (Optional)' },
  { code: 'AL', name: 'Alabama' }, { code: 'AK', name: 'Alaska' },
  { code: 'AZ', name: 'Arizona' }, { code: 'AR', name: 'Arkansas' },
  { code: 'CA', name: 'California' }, { code: 'CO', name: 'Colorado' },
  { code: 'CT', name: 'Connecticut' }, { code: 'DE', name: 'Delaware' },
  { code: 'FL', name: 'Florida' }, { code: 'GA', name: 'Georgia' },
  { code: 'HI', name: 'Hawaii' }, { code: 'ID', name: 'Idaho' },
  { code: 'IL', name: 'Illinois' }, { code: 'IN', name: 'Indiana' },
  { code: 'IA', name: 'Iowa' }, { code: 'KS', name: 'Kansas' },
  { code: 'KY', name: 'Kentucky' }, { code: 'LA', name: 'Louisiana' },
  { code: 'ME', name: 'Maine' }, { code: 'MD', name: 'Maryland' },
  { code: 'MA', name: 'Massachusetts' }, { code: 'MI', name: 'Michigan' },
  { code: 'MN', name: 'Minnesota' }, { code: 'MS', name: 'Mississippi' },
  { code: 'MO', name: 'Missouri' }, { code: 'MT', name: 'Montana' },
  { code: 'NE', name: 'Nebraska' }, { code: 'NV', name: 'Nevada' },
  { code: 'NH', name: 'New Hampshire' }, { code: 'NJ', name: 'New Jersey' },
  { code: 'NM', name: 'New Mexico' }, { code: 'NY', name: 'New York' },
  { code: 'NC', name: 'North Carolina' }, { code: 'ND', name: 'North Dakota' },
  { code: 'OH', name: 'Ohio' }, { code: 'OK', name: 'Oklahoma' },
  { code: 'OR', name: 'Oregon' }, { code: 'PA', name: 'Pennsylvania' },
  { code: 'RI', name: 'Rhode Island' }, { code: 'SC', name: 'South Carolina' },
  { code: 'SD', name: 'South Dakota' }, { code: 'TN', name: 'Tennessee' },
  { code: 'TX', name: 'Texas' }, { code: 'UT', name: 'Utah' },
  { code: 'VT', name: 'Vermont' }, { code: 'VA', name: 'Virginia' },
  { code: 'WA', name: 'Washington' }, { code: 'WV', name: 'West Virginia' },
  { code: 'WI', name: 'Wisconsin' }, { code: 'WY', name: 'Wyoming' }
];

function SuggestTournament({ isOpen, onClose }) {
  const { user } = useUser();
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    dates: '',
    state: ''
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const validateUrl = (url) => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error when user types
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError(null);

    const newErrors = {};

    // URL is required
    if (!formData.url.trim()) {
      newErrors.url = 'URL is required';
    } else if (!validateUrl(formData.url.trim())) {
      newErrors.url = 'Please enter a valid URL';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Create suggestion object
    const suggestion = {
      id: `sugg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      tournament_name: formData.name.trim() || '(Not provided)',
      tournament_url: formData.url.trim(),
      tournament_dates: formData.dates.trim() || '(Not provided)',
      tournament_state: formData.state || '(Not provided)',
      user_id: user?.id || 'anonymous',
      user_name: user?.name || 'Anonymous User',
      submitted_at: new Date().toISOString()
    };

    setSubmitting(true);

    try {
      // Submit to Formspree
      const response = await fetch(FORMSPREE_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(suggestion)
      });

      if (response.ok) {
        // Also save locally as backup
        saveSuggestionLocally(suggestion);

        // Show success
        setSubmitted(true);

        // Reset form after a delay
        setTimeout(() => {
          setFormData({ name: '', url: '', dates: '', state: '' });
          setSubmitted(false);
          onClose();
        }, 2500);
      } else {
        // If Formspree fails, save locally and show partial success
        saveSuggestionLocally(suggestion);
        setSubmitError('Submitted locally. Please export from Settings if online submission failed.');
        setSubmitted(true);
        setTimeout(() => {
          setFormData({ name: '', url: '', dates: '', state: '' });
          setSubmitted(false);
          setSubmitError(null);
          onClose();
        }, 3000);
      }
    } catch (error) {
      // Network error - save locally
      saveSuggestionLocally(suggestion);
      setSubmitError('Saved locally. Please export from Settings to send.');
      setSubmitted(true);
      setTimeout(() => {
        setFormData({ name: '', url: '', dates: '', state: '' });
        setSubmitted(false);
        setSubmitError(null);
        onClose();
      }, 3000);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Suggest a Tournament</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {submitted ? (
          <div className="success-message">
            <div className={`success-icon ${submitError ? 'warning' : ''}`}>
              {submitError ? '!' : '✓'}
            </div>
            <h3>{submitError ? 'Saved!' : 'Thank you!'}</h3>
            <p>
              {submitError || 'Your tournament suggestion has been submitted for review.'}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">
                Tournament URL <span className="required">*</span>
              </label>
              <input
                type="text"
                name="url"
                className={`form-input ${errors.url ? 'error' : ''}`}
                placeholder="https://example.com/tournament-schedule"
                value={formData.url}
                onChange={handleChange}
              />
              {errors.url && <span className="error-text">{errors.url}</span>}
              <span className="form-hint">Ideally a link to the tournament schedule page</span>
            </div>

            <div className="form-group">
              <label className="form-label">Tournament Name</label>
              <input
                type="text"
                name="name"
                className="form-input"
                placeholder="e.g., Spring Classic 2025"
                value={formData.name}
                onChange={handleChange}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Tournament Dates</label>
                <input
                  type="text"
                  name="dates"
                  className="form-input"
                  placeholder="e.g., March 15-17, 2025"
                  value={formData.dates}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label">State</label>
                <select
                  name="state"
                  className="form-select"
                  value={formData.state}
                  onChange={handleChange}
                >
                  {US_STATES.map(s => (
                    <option key={s.code} value={s.code}>{s.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-actions">
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Submitting...' : 'Submit Suggestion'}
              </button>
            </div>
          </form>
        )}

        <style>{`
          .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 1rem;
            box-sizing: border-box;
          }

          .modal-overlay *,
          .modal-overlay *::before,
          .modal-overlay *::after {
            box-sizing: border-box;
          }

          .modal-content {
            background: white;
            border-radius: 16px;
            width: calc(100% - 2rem);
            max-width: 500px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            margin: 0 auto;
          }

          .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid #e0e0e0;
          }

          .modal-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--primary-green);
            margin: 0;
          }

          .modal-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            color: #666;
            cursor: pointer;
            padding: 0.25rem;
            line-height: 1;
          }

          .modal-close:hover {
            color: #333;
          }

          form {
            padding: 1.5rem;
          }

          .form-group {
            margin-bottom: 1.25rem;
          }

          .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
          }

          .form-label {
            display: block;
            font-weight: 500;
            color: #333;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
          }

          .required {
            color: #dc3545;
          }

          .form-input,
          .form-select {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 0.95rem;
            transition: all 0.2s ease;
          }

          .form-input:focus,
          .form-select:focus {
            outline: none;
            border-color: var(--accent-green);
            box-shadow: 0 0 0 3px rgba(77, 133, 39, 0.1);
          }

          .form-input.error {
            border-color: #dc3545;
          }

          .error-text {
            color: #dc3545;
            font-size: 0.8rem;
            margin-top: 0.25rem;
            display: block;
          }

          .form-hint {
            color: #888;
            font-size: 0.8rem;
            margin-top: 0.25rem;
            display: block;
          }

          .form-actions {
            display: flex;
            gap: 1rem;
            justify-content: flex-end;
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid #e0e0e0;
          }

          .btn {
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
          }

          .btn-primary {
            background: var(--primary-green);
            color: white;
          }

          .btn-primary:hover {
            background: var(--accent-green);
          }

          .btn-secondary {
            background: #f5f5f5;
            color: #666;
          }

          .btn-secondary:hover {
            background: #e0e0e0;
          }

          .success-message {
            padding: 3rem 2rem;
            text-align: center;
          }

          .success-icon {
            width: 60px;
            height: 60px;
            background: #e8f5e9;
            color: var(--primary-green);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            margin: 0 auto 1rem;
          }

          .success-icon.warning {
            background: #fff3e0;
            color: #ef6c00;
          }

          .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
          }

          .success-message h3 {
            color: var(--primary-green);
            margin: 0 0 0.5rem;
          }

          .success-message p {
            color: #666;
            margin: 0;
          }

          @media (max-width: 480px) {
            .modal-overlay {
              padding: 0.5rem;
            }

            .modal-content {
              width: calc(100% - 1rem);
              border-radius: 12px;
              max-height: 95vh;
            }

            .modal-header {
              padding: 1rem;
            }

            .modal-title {
              font-size: 1.1rem;
            }

            form {
              padding: 1rem;
            }

            .form-row {
              grid-template-columns: 1fr;
            }

            .form-input,
            .form-select {
              font-size: 16px; /* Prevents zoom on iOS */
              padding: 0.65rem 0.75rem;
            }

            .form-actions {
              flex-direction: column-reverse;
              margin-top: 1rem;
              padding-top: 0.75rem;
            }

            .btn {
              width: 100%;
              padding: 0.7rem 1rem;
            }
          }
        `}</style>
      </div>
    </div>
  );
}

export default SuggestTournament;
