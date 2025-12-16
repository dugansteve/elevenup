/**
 * URL Validator Service for Seedline Frontend
 * 
 * This service handles communication with the URL validation backend
 * and provides helper functions for game verification.
 */

// API base URL - can be configured via environment
const API_BASE_URL = import.meta.env.VITE_VALIDATOR_URL || 'http://localhost:3001';

/**
 * Validate a single game's URL
 * @param {string} url - The URL to validate
 * @param {object} gameData - Game data to verify against
 * @returns {Promise<object>} Validation result
 */
export async function validateGameUrl(url, gameData) {
  if (!url) {
    return {
      success: false,
      verified: false,
      message: 'No URL provided',
      skipped: true
    };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/validate-url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url, gameData }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('URL validation error:', error);
    
    // Check if it's a network error (server not running)
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      return {
        success: false,
        verified: false,
        message: 'Validation server unavailable. Game will use community verification.',
        serverOffline: true,
        error: error.message
      };
    }
    
    return {
      success: false,
      verified: false,
      message: 'Validation failed: ' + error.message,
      error: error.message
    };
  }
}

/**
 * Validate multiple games in batch
 * @param {array} games - Array of games with scoreUrl property
 * @returns {Promise<object>} Batch validation results
 */
export async function validateGamesBatch(games) {
  const gamesWithUrls = games.filter(g => g.scoreUrl);
  
  if (gamesWithUrls.length === 0) {
    return { results: [], message: 'No games with URLs to validate' };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/validate-batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ games: gamesWithUrls }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Batch validation error:', error);
    return {
      results: [],
      error: error.message,
      serverOffline: true
    };
  }
}

/**
 * Check if the validation server is available
 * @returns {Promise<boolean>}
 */
export async function isValidatorAvailable() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000) // 3 second timeout
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Get validation status display info
 * @param {object} validationResult - Result from validateGameUrl
 * @returns {object} Display info with icon, text, and color
 */
export function getValidationDisplay(validationResult) {
  if (!validationResult) {
    return { icon: '⏳', text: 'Not checked', color: '#888' };
  }

  if (validationResult.skipped) {
    return { icon: '➖', text: 'No URL', color: '#888' };
  }

  if (validationResult.serverOffline) {
    return { icon: '🔌', text: 'Server offline', color: '#f57c00' };
  }

  if (validationResult.verified) {
    return { 
      icon: '✅', 
      text: `AI Verified (${validationResult.confidence}%)`, 
      color: '#388e3c',
      bg: '#e8f5e9'
    };
  }

  if (validationResult.confidence > 0) {
    return { 
      icon: '⚠️', 
      text: `Partial (${validationResult.confidence}%)`, 
      color: '#f57c00',
      bg: '#fff3e0'
    };
  }

  return { 
    icon: '❌', 
    text: 'Not verified', 
    color: '#c62828',
    bg: '#ffebee'
  };
}

/**
 * Format validation details for display
 * @param {object} validationResult - Result from validateGameUrl
 * @returns {array} Array of detail strings
 */
export function formatValidationDetails(validationResult) {
  if (!validationResult || !validationResult.details) {
    return [];
  }

  const details = [];
  const d = validationResult.details;

  if (d.matches) {
    if (d.matches.score) details.push('✓ Score matches');
    else details.push('✗ Score not found');
    
    if (d.matches.teams) details.push('✓ Teams found');
    else details.push('✗ Teams not found');
    
    if (d.matches.date) details.push('✓ Date matches');
    else details.push('✗ Date not found');
  }

  if (d.scoreFound) {
    details.push(`Found score: ${d.scoreFound}`);
  }

  if (d.dateFound) {
    details.push(`Found date: ${d.dateFound}`);
  }

  return details;
}

export default {
  validateGameUrl,
  validateGamesBatch,
  isValidatorAvailable,
  getValidationDisplay,
  formatValidationDetails
};
