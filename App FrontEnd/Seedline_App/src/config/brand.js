/**
 * Brand Configuration
 *
 * Determines branding at build time via VITE_BRAND environment variable.
 *
 * Build commands:
 *   npm run build:seedline  - Builds with Seedline branding
 *   npm run build:elevenup  - Builds with ElevenUp branding
 *
 * Local development:
 *   npm run dev             - Seedline branding (default)
 *   npm run dev:elevenup    - ElevenUp branding
 */

// Get brand from environment variable (set at build time)
const BRAND = import.meta.env.VITE_BRAND || 'elevenup';

/**
 * Brand-specific configuration
 */
export const BRAND_CONFIG = {
  seedline: {
    id: 'seedline',
    name: 'Seedline',
    logo: '/seedline-logo.png',
    tagline: null,
    supportEmail: 'support@seedline.ai',
    domain: 'seedline.ai',
    userAgent: 'SeedlineTournamentFinder/1.0',
    sessionKey: 'seedline_session_id',
    suggestionsKey: 'seedline_tournament_suggestions',
    firebaseProjectId: 'seedline-app',
    htmlTitle: 'Seedline - Soccer Rankings & Player Badges',
    colors: {
      star: '#FFD700',      // Gold stars
      accent: '#f59e0b',
      linkManager: '#FFD700'
    }
  },
  elevenup: {
    id: 'elevenup',
    name: 'ElevenUp',
    logo: '/elevenup-logo.png',
    tagline: null,  // Logo already includes "Youth Soccer Rankings"
    supportEmail: 'support@elevenup.ai',
    domain: 'elevenup.ai',
    userAgent: 'ElevenUpTournamentFinder/1.0',
    sessionKey: 'elevenup_session_id',
    suggestionsKey: 'elevenup_tournament_suggestions',
    firebaseProjectId: 'elevenup',
    htmlTitle: 'ElevenUp - Soccer Rankings & Player Badges',
    colors: {
      star: '#76FF03',      // Neon green stars
      accent: '#1DE9B6',
      linkManager: '#76FF03'
    }
  }
};

// Export the current brand configuration
export const currentBrand = BRAND_CONFIG[BRAND] || BRAND_CONFIG.seedline;

// Export convenience boolean for ElevenUp-specific logic
export const isElevenUpBrand = BRAND === 'elevenup';

// Export the brand ID
export const brandId = BRAND;
