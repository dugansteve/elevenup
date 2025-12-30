import { useEffect, useRef, useMemo, useState, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { getTeamCoordinates, getRankColor, loadClubAddresses, getFormattedAddress } from '../data/clubCoordinates';

// Create a numbered pin icon
function createNumberedIcon(rank, color, teamName = null) {
  const size = rank <= 10 ? 24 : rank <= 99 ? 22 : 20;
  const fontSize = rank <= 10 ? 11 : rank <= 99 ? 9 : 7;

  // If team name should be shown, create a wider icon with label
  if (teamName) {
    return L.divIcon({
      className: 'numbered-marker labeled-marker',
      html: `<div style="display: flex; align-items: center; gap: 4px;">
        <div style="
          background-color: ${color};
          color: white;
          width: ${size}px;
          height: ${size}px;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          border: 2px solid #333;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: ${fontSize}px;
          font-weight: bold;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
          flex-shrink: 0;
        "><span style="transform: rotate(45deg);">${rank}</span></div>
        <span style="
          background: rgba(255,255,255,0.95);
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
          color: #333;
          white-space: nowrap;
          box-shadow: 0 1px 3px rgba(0,0,0,0.2);
          border: 1px solid #ddd;
        ">${teamName}</span>
      </div>`,
      iconSize: [size + 150, size],
      iconAnchor: [size / 2, size],
      popupAnchor: [0, -size]
    });
  }

  return L.divIcon({
    className: 'numbered-marker',
    html: `<div style="
      background-color: ${color};
      color: white;
      width: ${size}px;
      height: ${size}px;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      border: 2px solid #333;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: ${fontSize}px;
      font-weight: bold;
      box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    "><span style="transform: rotate(45deg);">${rank}</span></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size]
  });
}

function FitBounds({ teams }) {
  const map = useMap();
  useEffect(() => {
    if (teams.length === 0) return;
    const bounds = teams
      .filter(team => team.coords?.lat != null && team.coords?.lng != null)
      .map(team => [team.coords.lat, team.coords.lng]);
    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [teams, map]);
  return null;
}

function ZoomTracker({ onZoomChange, onBoundsChange }) {
  const map = useMapEvents({
    zoomend: () => {
      onZoomChange(map.getZoom());
      onBoundsChange(map.getBounds());
    },
    moveend: () => {
      onBoundsChange(map.getBounds());
    }
  });
  useEffect(() => {
    onZoomChange(map.getZoom());
    onBoundsChange(map.getBounds());
  }, [map, onZoomChange, onBoundsChange]);
  return null;
}

// Extract base club name by stripping age group suffixes
// "Lamorinda SC 13G" -> "Lamorinda SC"
// "TopHat 08G Gold" -> "TopHat"
// "1974 Newark FC 08/07G" -> "1974 Newark FC"
function extractBaseClubName(clubName) {
  if (!clubName) return 'Unknown';

  let result = clubName;

  // Protect 4-digit years at the start (like "1974 Newark FC")
  let protectedStart = '';
  const startMatch = result.match(/^(\d{4}\s+)/);
  if (startMatch) {
    protectedStart = startMatch[1];
    result = result.substring(protectedStart.length);
  }

  // Remove age patterns ANYWHERE in the string (not just end):
  // "08/07G", "08/07"
  result = result.replace(/\s+\d{2}\/\d{2}[GB]?/gi, '');
  // "13G", "B14", "G13", "08G", "B2012", "G2012", "2012", "2013"
  result = result.replace(/\s+[GB]?\d{2,4}[GB]?(?=\s|$)/gi, '');

  // Remove league suffixes
  result = result.replace(/\s+(GA|ECNL|ECNL-RL|NPL|RL|Pre-Academy|Academy|Elite|Select|Premier)(\s+(Navy|Red|Blue|White|Black|Gold|Silver))?/gi, '');

  // Remove color suffixes
  result = result.replace(/\s+(Navy|Red|Blue|White|Black|Gold|Silver|Orange|Green|Purple)$/i, '');

  // Restore protected start and trim
  result = (protectedStart + result).trim();

  return result || clubName;
}

// Organize teams into grid layout:
// - Teams from same club at same location: HORIZONTAL row (different lng, same lat)
// - Different clubs at same location: VERTICAL separation (different lat for each club row)
function calculateOrganizedPositions(teams, zoomLevel) {
  // Group teams by location (rounded coordinates for grouping)
  const precision = 2; // ~1km grouping
  const locationGroups = {};

  teams.forEach(team => {
    const lat = team.coords?.lat ?? 39.8283;
    const lng = team.coords?.lng ?? -98.5795;
    const locKey = lat.toFixed(precision) + "," + lng.toFixed(precision);
    if (!locationGroups[locKey]) {
      locationGroups[locKey] = {
        baseLat: lat,
        baseLng: lng,
        clubs: {}
      };
    }

    // Use normalized club name for grouping
    const baseClubName = extractBaseClubName(team.club);

    if (!locationGroups[locKey].clubs[baseClubName]) {
      locationGroups[locKey].clubs[baseClubName] = [];
    }
    locationGroups[locKey].clubs[baseClubName].push(team);
  });

  // Calculate spacing based on zoom level
  // Higher zoom = smaller degree offset needed (pins appear same size on screen)
  const baseSpacing = 0.008 * Math.pow(2, 10 - zoomLevel);
  const minSpacing = 0.0008; // Minimum to keep pins from overlapping
  const spacing = Math.max(minSpacing, baseSpacing);

  const result = [];

  Object.values(locationGroups).forEach(location => {
    const clubNames = Object.keys(location.clubs).sort();
    const numClubs = clubNames.length;

    clubNames.forEach((clubName, clubIndex) => {
      const clubTeams = location.clubs[clubName];
      const numTeams = clubTeams.length;

      // Sort teams by rank within club for consistent ordering
      clubTeams.sort((a, b) => a.rank - b.rank);

      // VERTICAL offset for different clubs (each club on its own row)
      // Offset in latitude (north-south)
      const verticalOffset = numClubs > 1
        ? (clubIndex - (numClubs - 1) / 2) * spacing * 1.2
        : 0;

      clubTeams.forEach((team, teamIndex) => {
        // HORIZONTAL offset for teams in same club (spread along the row)
        // Offset in longitude (east-west)
        const horizontalOffset = numTeams > 1
          ? (teamIndex - (numTeams - 1) / 2) * spacing * 1.2
          : 0;

        result.push({
          ...team,
          displayLat: location.baseLat + verticalOffset,
          displayLng: location.baseLng + horizontalOffset,
          baseClubName: clubName // For debugging
        });
      });
    });
  });

  return result;
}

function RankingsMap({ teams, onClose }) {
  const mapRef = useRef(null);
  const [zoomLevel, setZoomLevel] = useState(4);
  const [addressesLoaded, setAddressesLoaded] = useState(false);
  const [teamLimit, setTeamLimit] = useState('all'); // 'top10', 'top100', or 'all'
  const [mapBounds, setMapBounds] = useState(null);

  // Load club addresses on mount
  useEffect(() => {
    loadClubAddresses().then(() => {
      setAddressesLoaded(true);
    });
  }, []);

  // Filter teams based on selected limit
  const filteredTeams = useMemo(() => {
    if (teamLimit === 'top10') return teams.slice(0, 10);
    if (teamLimit === 'top100') return teams.slice(0, 100);
    return teams;
  }, [teams, teamLimit]);

  const teamsWithCoords = useMemo(() => {
    return filteredTeams.map((team, index) => {
      const coords = getTeamCoordinates(team) || { lat: 39.8283, lng: -98.5795 };
      return {
        ...team,
        rank: index + 1,
        coords,
        color: getRankColor(index + 1, filteredTeams.length),
        address: getFormattedAddress(team)
      };
    });
  }, [filteredTeams, addressesLoaded]);

  const organizedTeams = useMemo(() => {
    return calculateOrganizedPositions(teamsWithCoords, zoomLevel);
  }, [teamsWithCoords, zoomLevel]);

  // Count visible teams in current viewport
  const visibleTeamsCount = useMemo(() => {
    if (!mapBounds) return organizedTeams.length;
    return organizedTeams.filter(team =>
      mapBounds.contains([team.displayLat, team.displayLng])
    ).length;
  }, [organizedTeams, mapBounds]);

  const showLabels = visibleTeamsCount <= 15;

  const handleZoomChange = useCallback((zoom) => { setZoomLevel(zoom); }, []);
  const handleBoundsChange = useCallback((bounds) => { setMapBounds(bounds); }, []);

  const defaultCenter = [39.8283, -98.5795];
  const defaultZoom = 4;

  return (
    <div className="map-overlay">
      <div className="map-container">
        <div className="map-header">
          <h2 className="map-title">Team Rankings Map ({filteredTeams.length} teams)</h2>
          <div className="map-controls">
            <select 
              className="map-limit-select"
              value={teamLimit}
              onChange={(e) => setTeamLimit(e.target.value)}
            >
              <option value="top10">Top 10</option>
              <option value="top100">Top 100</option>
              <option value="all">All Teams ({teams.length})</option>
            </select>
            <button className="map-close-btn" onClick={onClose}>Close Map</button>
          </div>
        </div>

        <div className="map-legend">
          <span className="legend-label">Rank:</span>
          <div className="legend-gradient">
            <span className="legend-start">#1 (Best)</span>
            <div className="gradient-bar"></div>
            <span className="legend-end">#{filteredTeams.length} (Lowest)</span>
          </div>
        </div>

        <div className="map-wrapper">
          <MapContainer
            ref={mapRef}
            center={defaultCenter}
            zoom={defaultZoom}
            style={{ height: '100%', width: '100%', touchAction: 'none' }}
            scrollWheelZoom={true}
            touchZoom={true}
            dragging={true}
            tap={true}
          >
            <TileLayer
              attribution='&copy; OpenStreetMap contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitBounds teams={teamsWithCoords} />
            <ZoomTracker onZoomChange={handleZoomChange} onBoundsChange={handleBoundsChange} />

            {[...organizedTeams].reverse().map((team, idx) => (
              <Marker
                key={team.id || `team-${idx}`}
                position={[team.displayLat, team.displayLng]}
                icon={createNumberedIcon(team.rank, team.color, showLabels ? team.name : null)}
              >
                <Popup>
                  <div className="map-popup">
                    <div className="popup-rank" style={{ backgroundColor: team.color }}>#{team.rank}</div>
                    <div className="popup-content">
                      <div className="popup-team-name">{team.name} {team.ageGroup}</div>
                      <div className="popup-club">{team.club}</div>
                      {team.address && <div className="popup-address">{team.address}</div>}
                      <div className="popup-details">
                        <span className="popup-league" style={{ background: team.league === 'ECNL' ? '#e3f2fd' : '#f3e5f5', color: team.league === 'ECNL' ? '#1976d2' : '#7b1fa2' }}>{team.league}</span>
                        <span className="popup-state">{team.state}</span>
                      </div>
                      <div className="popup-stats">
                        <span>Power Score: <strong>{team.powerScore ? team.powerScore.toFixed(1) : 'N/A'}</strong></span>
                        <span>Record: <strong>{team.wins ?? 0}-{team.losses ?? 0}-{team.draws ?? 0}</strong></span>
                      </div>
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>

        <div className="map-footer">
          <p className="map-note">Click on any marker to see team details. Same club = horizontal row, different clubs = vertical rows.</p>
        </div>
      </div>
    </div>
  );
}

export default RankingsMap;
