// Flat style icons - clean, minimal, no shadows
// Simple geometric shapes with solid fills

// Color palettes
const colors = {
  green: {
    primary: '#2D5016',
    secondary: '#4A7C2A',
    accent: '#6BA340',
  },
  gray: {
    primary: '#3A3A3A',
    secondary: '#666666',
    accent: '#888888',
  },
  white: {
    primary: '#FFFFFF',
    secondary: '#F0F0F0',
    accent: '#E0E0E0',
  },
  // ElevenUp theme - blue/green/cyan tones with shading
  elevenup: {
    primary: '#00E676',    // Bright green
    secondary: '#00BCD4',  // Cyan
    accent: '#4DD0E1',     // Light cyan
  }
};

// Teams - Trophy icon
export function TeamsIcon({ size = 24, color = 'green' }) {
  const c = colors[color] || colors.green;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {/* Trophy cup */}
      <path
        d="M7 4h10v8c0 2.76-2.24 5-5 5s-5-2.24-5-5V4z"
        fill={c.primary}
      />
      {/* Left handle */}
      <path
        d="M7 6H4c0 2.5 1.5 4 3 4V6z"
        fill={c.secondary}
      />
      {/* Right handle */}
      <path
        d="M17 6h3c0 2.5-1.5 4-3 4V6z"
        fill={c.secondary}
      />
      {/* Base */}
      <rect x="9" y="17" width="6" height="2" fill={c.secondary} />
      <rect x="7" y="19" width="10" height="2" rx="1" fill={c.primary} />
    </svg>
  );
}

// Clubs - Shield with soccer ball
export function ClubsIcon({ size = 24, color = 'green' }) {
  const c = colors[color] || colors.green;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {/* Shield */}
      <path
        d="M12 2L4 5v6c0 5.55 3.42 10.74 8 12 4.58-1.26 8-6.45 8-12V5l-8-3z"
        fill={c.primary}
      />
      {/* Soccer ball pentagon */}
      <path
        d="M12 8l2.5 1.8-1 3.2h-3l-1-3.2L12 8z"
        fill="white"
      />
    </svg>
  );
}

// Players - Two person silhouettes
export function PlayersIcon({ size = 24, color = 'green' }) {
  const c = colors[color] || colors.green;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {/* Back person */}
      <circle cx="16" cy="7" r="3" fill={c.secondary} />
      <path
        d="M12 21v-4c0-2.21 1.79-4 4-4s4 1.79 4 4v4h-8z"
        fill={c.secondary}
      />
      {/* Front person */}
      <circle cx="9" cy="8" r="3.5" fill={c.primary} />
      <path
        d="M3 21v-3c0-2.76 2.24-5 5-5h2c2.76 0 5 2.24 5 5v3H3z"
        fill={c.primary}
      />
    </svg>
  );
}

// Badges - Medal/ribbon
export function BadgesIcon({ size = 24, color = 'green' }) {
  const c = colors[color] || colors.green;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {/* Ribbon tails */}
      <path d="M8 13v9l4-3 4 3v-9" fill={c.secondary} />
      {/* Medal circle */}
      <circle cx="12" cy="9" r="7" fill={c.primary} />
      {/* Star on medal */}
      <path
        d="M12 5l1.12 3.45h3.63l-2.94 2.13 1.12 3.45L12 11.9l-2.93 2.13 1.12-3.45-2.94-2.13h3.63L12 5z"
        fill="white"
      />
    </svg>
  );
}

// Simulation - Bar chart
export function SimulationIcon({ size = 24, color = 'green' }) {
  const c = colors[color] || colors.green;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {/* Bars */}
      <rect x="4" y="13" width="4" height="8" rx="1" fill={c.secondary} />
      <rect x="10" y="7" width="4" height="14" rx="1" fill={c.primary} />
      <rect x="16" y="10" width="4" height="11" rx="1" fill={c.accent} />
      {/* Trend line */}
      <path
        d="M4 11l6-5 6 3 4-4"
        stroke={c.primary}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="20" cy="5" r="2" fill={c.primary} />
    </svg>
  );
}

// Tournament - Map pin/location
export function TournamentIcon({ size = 24, color = 'green' }) {
  const c = colors[color] || colors.green;
  const dotColor = color === 'white' ? colors.green.primary : 'white';
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {/* Pin */}
      <path
        d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"
        fill={c.primary}
      />
      {/* Inner circle */}
      <circle cx="12" cy="9" r="3" fill={dotColor} />
    </svg>
  );
}

// Settings - Gear
export function SettingsIcon({ size = 24, color = 'green' }) {
  const c = colors[color] || colors.green;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.44.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"
        fill={c.primary}
      />
    </svg>
  );
}

// Logout - Door with arrow
export function LogoutIcon({ size = 24, color = 'green' }) {
  const c = colors[color] || colors.green;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {/* Door frame */}
      <path
        d="M5 3h8c1.1 0 2 .9 2 2v4h-2V5H5v14h8v-4h2v4c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2V5c0-1.1.9-2 2-2z"
        fill={c.primary}
      />
      {/* Arrow */}
      <path
        d="M16 12l-4-4v3H9v2h3v3l4-4z"
        fill={c.secondary}
      />
      <rect x="17" y="11" width="4" height="2" fill={c.secondary} />
    </svg>
  );
}

// Export all icons as a collection
export const PaperIcons = {
  teams: TeamsIcon,
  clubs: ClubsIcon,
  players: PlayersIcon,
  badges: BadgesIcon,
  simulation: SimulationIcon,
  tournament: TournamentIcon,
  settings: SettingsIcon,
  logout: LogoutIcon
};

export default PaperIcons;
