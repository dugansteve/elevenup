// Club coordinates lookup system
// Uses pre-computed coordinates from club_addresses.json
// V2: Added cache-busting to prevent stale data

let clubAddresses = null;
let addressesLoaded = false;

// Cache-busting: 15-minute window so users don't re-download on every page load
const getCacheBuster = () => {
  const now = Date.now();
  const window15min = Math.floor(now / (15 * 60 * 1000));
  return `v=${window15min}`;
};

const STATE_NAME_TO_ABBREV = {
  'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
  'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
  'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
  'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
  'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
  'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
  'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
  'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
  'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
  'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
  'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
  'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
  'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC'
};

export const STATE_CENTROIDS = {
  "AL": { lat: 32.806671, lng: -86.791130 },
  "AK": { lat: 64.200841, lng: -152.493782 },
  "AZ": { lat: 33.729759, lng: -111.431221 },
  "AR": { lat: 34.799999, lng: -92.199997 },
  "CA": { lat: 36.116203, lng: -119.681564 },
  "CO": { lat: 39.059811, lng: -105.311104 },
  "CT": { lat: 41.597782, lng: -72.755371 },
  "DC": { lat: 38.897438, lng: -77.026817 },
  "DE": { lat: 39.145, lng: -75.419 },
  "FL": { lat: 27.766279, lng: -81.686783 },
  "GA": { lat: 33.040619, lng: -83.643074 },
  "HI": { lat: 21.094318, lng: -157.498337 },
  "ID": { lat: 44.240459, lng: -114.478828 },
  "IL": { lat: 40.349457, lng: -88.986137 },
  "IN": { lat: 39.849426, lng: -86.258278 },
  "IA": { lat: 42.011539, lng: -93.210526 },
  "KS": { lat: 38.526600, lng: -96.726486 },
  "KY": { lat: 37.668140, lng: -84.670067 },
  "LA": { lat: 31.169546, lng: -91.867805 },
  "ME": { lat: 44.693947, lng: -69.381927 },
  "MD": { lat: 39.063946, lng: -76.802101 },
  "MA": { lat: 42.230171, lng: -71.530106 },
  "MI": { lat: 43.326618, lng: -84.536095 },
  "MN": { lat: 45.694454, lng: -93.900192 },
  "MS": { lat: 32.741646, lng: -89.678696 },
  "MO": { lat: 38.456085, lng: -92.288368 },
  "MT": { lat: 46.921925, lng: -110.454353 },
  "NE": { lat: 41.125370, lng: -98.268082 },
  "NV": { lat: 38.313515, lng: -117.055374 },
  "NH": { lat: 43.452492, lng: -71.563896 },
  "NJ": { lat: 40.298904, lng: -74.521011 },
  "NM": { lat: 34.840515, lng: -106.248482 },
  "NY": { lat: 42.165726, lng: -74.948051 },
  "NC": { lat: 35.630066, lng: -79.806419 },
  "ND": { lat: 47.528912, lng: -99.784012 },
  "OH": { lat: 40.388783, lng: -82.764915 },
  "OK": { lat: 35.565342, lng: -96.928917 },
  "OR": { lat: 44.572021, lng: -122.070938 },
  "PA": { lat: 40.590752, lng: -77.209755 },
  "RI": { lat: 41.680893, lng: -71.511780 },
  "SC": { lat: 33.856892, lng: -80.945007 },
  "SD": { lat: 44.299782, lng: -99.438828 },
  "TN": { lat: 35.747845, lng: -86.692345 },
  "TX": { lat: 31.054487, lng: -97.563461 },
  "UT": { lat: 40.150032, lng: -111.862434 },
  "VT": { lat: 44.045876, lng: -72.710686 },
  "VA": { lat: 37.769337, lng: -78.169968 },
  "WA": { lat: 47.400902, lng: -121.490494 },
  "WV": { lat: 38.491226, lng: -80.954456 },
  "WI": { lat: 44.268543, lng: -89.616508 },
  "WY": { lat: 42.755966, lng: -107.302490 }
};

function normalizeState(state) {
  if (!state) return '';
  const s = state.trim();
  if (s.length === 2) return s.toUpperCase();
  const lower = s.toLowerCase();
  return STATE_NAME_TO_ABBREV[lower] || s.toUpperCase();
}

export async function loadClubAddresses() {
  if (addressesLoaded) return clubAddresses;
  try {
    const response = await fetch(`/club_addresses.json?${getCacheBuster()}`);
    if (response.ok) {
      clubAddresses = await response.json();
      addressesLoaded = true;
      console.log('Loaded club addresses:', Object.keys(clubAddresses.clubs || {}).length, 'clubs');
    }
  } catch (e) {
    console.warn('Could not load club addresses:', e);
  }
  return clubAddresses;
}

export function setClubAddresses(addresses) {
  clubAddresses = addresses;
  addressesLoaded = true;
}

// Helper to normalize club name for matching
function normalizeClubName(name) {
  if (!name) return '';
  return name.toLowerCase()
    .replace(/\s+(sc|fc|soccer club|soccer|club|youth|academy|united)$/i, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function getClubAddress(clubName, teamName) {
  if (!clubAddresses) return null;

  // Try exact team name match first (most specific)
  if (teamName && clubAddresses.teams && clubAddresses.teams[teamName]) {
    const addr = clubAddresses.teams[teamName];
    if (addr.lat) return addr;
  }

  // Try exact club name match
  if (clubName && clubAddresses.clubs && clubAddresses.clubs[clubName]) {
    const addr = clubAddresses.clubs[clubName];
    if (addr.lat) return addr;
  }

  // Try partial/fuzzy club name match
  if (clubName && clubAddresses.clubs) {
    const clubLower = clubName.toLowerCase();
    const clubNorm = normalizeClubName(clubName);

    for (const [name, addr] of Object.entries(clubAddresses.clubs)) {
      if (!addr.lat) continue; // Skip entries without coordinates

      const nameLower = name.toLowerCase();
      const nameNorm = normalizeClubName(name);

      // Exact match after normalization
      if (nameNorm === clubNorm && clubNorm.length > 3) {
        return addr;
      }

      // One starts with the other (at least 5 chars)
      if ((nameLower.startsWith(clubLower) && clubLower.length > 5) ||
          (clubLower.startsWith(nameLower) && nameLower.length > 5)) {
        return addr;
      }

      // Normalized prefix match
      if ((nameNorm.startsWith(clubNorm) && clubNorm.length > 4) ||
          (clubNorm.startsWith(nameNorm) && nameNorm.length > 4)) {
        return addr;
      }
    }
  }

  // Try partial team name match in teams collection
  if (teamName && clubAddresses.teams) {
    const teamLower = teamName.toLowerCase();
    for (const [name, addr] of Object.entries(clubAddresses.teams)) {
      if (!addr.lat) continue;
      const nameLower = name.toLowerCase();
      // Match if team name starts with stored name (handles "Beach FC G13" matching "Beach FC 13G GA")
      if (teamLower.startsWith(nameLower.substring(0, 15)) && nameLower.length > 10) {
        return addr;
      }
    }
  }

  return null;
}

// Get exact base coordinates for a team (no offset - used for grouping)
export function getTeamBaseCoordinates(team) {
  const address = getClubAddress(team.club, team.name);

  // Use pre-computed coordinates from address if available
  if (address && address.lat && address.lng) {
    return { lat: address.lat, lng: address.lng, source: 'address' };
  }

  // Fall back to state centroid from address
  if (address && address.state) {
    const state = normalizeState(address.state);
    if (state && STATE_CENTROIDS[state]) {
      return { ...STATE_CENTROIDS[state], source: 'state' };
    }
  }

  // Fall back to team's state
  const teamState = normalizeState(team.state);
  if (teamState && STATE_CENTROIDS[teamState]) {
    return { ...STATE_CENTROIDS[teamState], source: 'state' };
  }

  // Default to center of continental US
  return { lat: 39.8283, lng: -98.5795, source: 'default' };
}

// Legacy function - returns exact coordinates (positioning handled by map component)
export function getTeamCoordinates(team) {
  return getTeamBaseCoordinates(team);
}

export function getFormattedAddress(team) {
  const address = getClubAddress(team.club, team.name);
  if (!address) return null;

  const parts = [];
  if (address.streetAddress) parts.push(address.streetAddress);
  if (address.city) parts.push(address.city);
  if (address.state) parts.push(normalizeState(address.state));
  if (address.zipCode) parts.push(address.zipCode);

  return parts.length > 0 ? parts.join(', ') : null;
}

export function getRankColor(rank, totalTeams) {
  if (totalTeams <= 1) return '#006400';
  const position = (rank - 1) / (totalTeams - 1);
  const colors = [
    { pos: 0, r: 0, g: 100, b: 0 },
    { pos: 0.15, r: 34, g: 139, b: 34 },
    { pos: 0.30, r: 154, g: 205, b: 50 },
    { pos: 0.45, r: 255, g: 215, b: 0 },
    { pos: 0.60, r: 255, g: 165, b: 0 },
    { pos: 0.75, r: 255, g: 69, b: 0 },
    { pos: 0.90, r: 178, g: 34, b: 34 },
    { pos: 1, r: 139, g: 0, b: 0 }
  ];
  let lower = colors[0];
  let upper = colors[colors.length - 1];
  for (let i = 0; i < colors.length - 1; i++) {
    if (position >= colors[i].pos && position <= colors[i + 1].pos) {
      lower = colors[i];
      upper = colors[i + 1];
      break;
    }
  }
  const range = upper.pos - lower.pos;
  const factor = range === 0 ? 0 : (position - lower.pos) / range;
  const r = Math.round(lower.r + (upper.r - lower.r) * factor);
  const g = Math.round(lower.g + (upper.g - lower.g) * factor);
  const b = Math.round(lower.b + (upper.b - lower.b) * factor);
  return `rgb(${r}, ${g}, ${b})`;
}
