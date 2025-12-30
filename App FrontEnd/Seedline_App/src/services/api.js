/**
 * Seedline API Client
 *
 * Handles all API communication with the backend, including:
 * - Authentication token management
 * - Session tracking
 * - Activity logging
 * - Rate limit handling
 */

import { collectFingerprint } from './fingerprint';
import { currentBrand } from '../config/brand';

// API base URL - uses relative path for same-origin, or can be configured
const API_BASE = import.meta.env.VITE_API_URL || '';

// Session storage key - brand-specific
const SESSION_KEY = currentBrand.sessionKey;

class SeedlineAPI {
  constructor() {
    this.sessionId = localStorage.getItem(SESSION_KEY);
    this.authToken = null;
    this.accountType = 'guest';
    this.currentPageViewId = null;
    this.pageStartTime = null;
    this.previousPage = null;
    this.previousEntityId = null;
    this.heartbeatInterval = null;
  }

  /**
   * Set the Firebase auth token for authenticated requests
   */
  setAuthToken(token) {
    this.authToken = token;
  }

  /**
   * Get headers for API requests
   */
  async getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
    }

    return headers;
  }

  /**
   * Initialize a tracking session
   */
  async initSession() {
    try {
      // Collect device fingerprint
      const fingerprint = await collectFingerprint();

      // Parse UTM params from URL
      const params = new URLSearchParams(window.location.search);

      const deviceInfo = {
        ...fingerprint,
        referrer: document.referrer,
        landingPage: window.location.pathname,
        utm_source: params.get('utm_source'),
        utm_medium: params.get('utm_medium'),
        utm_campaign: params.get('utm_campaign'),
        utm_term: params.get('utm_term'),
        utm_content: params.get('utm_content'),
      };

      const response = await this.post('/api/v1/activity/session', deviceInfo);

      if (response.session_id) {
        this.sessionId = response.session_id;
        this.accountType = response.account_type || 'guest';
        localStorage.setItem(SESSION_KEY, this.sessionId);
        console.log('[API] Session initialized:', this.sessionId);
      }

      return this.sessionId;
    } catch (error) {
      console.warn('[API] Failed to initialize session:', error);
      // Generate a local session ID as fallback
      this.sessionId = `local_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem(SESSION_KEY, this.sessionId);
      return this.sessionId;
    }
  }

  /**
   * Update session with authenticated user info
   */
  async updateSessionUser() {
    if (!this.sessionId || !this.authToken) return;

    try {
      const response = await this.post('/api/v1/activity/update-user', {
        session_id: this.sessionId
      });

      if (response.account_type) {
        this.accountType = response.account_type;
      }

      return response;
    } catch (error) {
      console.warn('[API] Failed to update session user:', error);
    }
  }

  /**
   * Make a GET request
   */
  async get(endpoint, params = {}) {
    const url = new URL(API_BASE + endpoint, window.location.origin);

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.append(key, value);
      }
    });

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: await this.getHeaders(),
      });

      // Handle rate limiting
      if (response.status === 429) {
        const retryAfter = response.headers.get('X-RateLimit-Reset') || 60;
        console.warn(`[API] Rate limited. Retry after ${retryAfter}s`);
        throw new Error(`Rate limited. Please try again in ${retryAfter} seconds.`);
      }

      return response.json();
    } catch (error) {
      console.error('[API] GET error:', endpoint, error);
      throw error;
    }
  }

  /**
   * Make a POST request
   */
  async post(endpoint, body = {}) {
    try {
      const response = await fetch(API_BASE + endpoint, {
        method: 'POST',
        headers: await this.getHeaders(),
        body: JSON.stringify(body),
      });

      if (response.status === 429) {
        const data = await response.json();
        throw new Error(data.error || 'Rate limited');
      }

      return response.json();
    } catch (error) {
      console.error('[API] POST error:', endpoint, error);
      throw error;
    }
  }

  /**
   * Make a DELETE request
   */
  async delete(endpoint) {
    try {
      const response = await fetch(API_BASE + endpoint, {
        method: 'DELETE',
        headers: await this.getHeaders(),
      });

      if (response.status === 429) {
        throw new Error('Rate limited');
      }

      return response.json();
    } catch (error) {
      console.error('[API] DELETE error:', endpoint, error);
      throw error;
    }
  }

  // ========== RANKINGS API ==========

  /**
   * Get rankings with optional filters
   */
  async getRankings(filters = {}) {
    return this.get('/api/v1/rankings', filters);
  }

  /**
   * Get a single team by ID or name
   */
  async getTeam(teamId) {
    return this.get(`/api/v1/rankings/team/${encodeURIComponent(teamId)}`);
  }

  /**
   * Get all teams for a club
   */
  async getClub(clubName) {
    return this.get(`/api/v1/rankings/club/${encodeURIComponent(clubName)}`);
  }

  /**
   * Search teams, clubs, and players
   */
  async search(query, type = 'all', limit = 20) {
    return this.get('/api/v1/rankings/search', { q: query, type, limit });
  }

  // ========== ACTIVITY TRACKING ==========

  /**
   * Track a page view
   */
  async trackPageView(pageType, pagePath, entity = null) {
    if (!this.sessionId) {
      await this.initSession();
    }

    // Send heartbeat for previous page if exists
    if (this.currentPageViewId && this.pageStartTime) {
      const timeOnPage = Date.now() - this.pageStartTime;
      this.sendHeartbeat(timeOnPage);
    }

    // Clear previous heartbeat interval
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    try {
      const response = await this.post('/api/v1/activity/pageview', {
        session_id: this.sessionId,
        page_type: pageType,
        page_path: pagePath,
        entity_type: entity?.type,
        entity_id: entity?.id,
        entity_name: entity?.name,
        previous_page: this.previousPage,
        previous_entity_id: this.previousEntityId,
        navigation_method: this.getNavigationMethod(),
      });

      this.currentPageViewId = response.page_view_id;
      this.pageStartTime = Date.now();
      this.previousPage = pagePath;
      this.previousEntityId = entity?.id;

      // Set up periodic heartbeat (every 30 seconds)
      this.heartbeatInterval = setInterval(() => {
        if (this.currentPageViewId && this.pageStartTime) {
          const timeOnPage = Date.now() - this.pageStartTime;
          this.sendHeartbeat(timeOnPage);
        }
      }, 30000);

      return response;
    } catch (error) {
      console.warn('[API] Failed to track page view:', error);
    }
  }

  /**
   * Send heartbeat to update time on page
   */
  async sendHeartbeat(timeOnPageMs, maxScrollDepth = null) {
    if (!this.currentPageViewId) return;

    try {
      await this.post('/api/v1/activity/heartbeat', {
        page_view_id: this.currentPageViewId,
        time_on_page_ms: timeOnPageMs,
        max_scroll_depth: maxScrollDepth,
      });
    } catch (error) {
      // Silently fail heartbeats
    }
  }

  /**
   * Detect navigation method
   */
  getNavigationMethod() {
    if (performance && performance.getEntriesByType) {
      const navEntry = performance.getEntriesByType('navigation')[0];
      if (navEntry) {
        switch (navEntry.type) {
          case 'navigate': return 'click';
          case 'reload': return 'reload';
          case 'back_forward': return 'back';
          default: return 'direct';
        }
      }
    }
    return 'unknown';
  }

  /**
   * Clean up on page unload
   */
  cleanup() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    // Send final heartbeat synchronously
    if (this.currentPageViewId && this.pageStartTime) {
      const timeOnPage = Date.now() - this.pageStartTime;
      navigator.sendBeacon(
        API_BASE + '/api/v1/activity/heartbeat',
        JSON.stringify({
          page_view_id: this.currentPageViewId,
          time_on_page_ms: timeOnPage,
        })
      );
    }
  }
}

// Create singleton instance
export const api = new SeedlineAPI();

// Set up cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => api.cleanup());
  window.addEventListener('pagehide', () => api.cleanup());
}

export default api;
