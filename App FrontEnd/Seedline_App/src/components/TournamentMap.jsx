import { useState, useEffect, useRef, useCallback } from 'react';
import { TournamentIcon } from './PaperIcons';
import { currentBrand } from '../config/brand';

// Haversine formula to calculate distance between two lat/lng points
function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 3959; // Earth's radius in miles
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

// Load Leaflet CSS and JS dynamically (including MarkerCluster plugin)
function loadLeaflet() {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    if (window.L && window.L.markerClusterGroup) {
      resolve(window.L);
      return;
    }

    // Load Leaflet CSS
    if (!document.querySelector('link[href*="leaflet.css"]')) {
      const css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      css.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
      css.crossOrigin = '';
      document.head.appendChild(css);
    }

    // Load MarkerCluster CSS
    if (!document.querySelector('link[href*="MarkerCluster.css"]')) {
      const clusterCss = document.createElement('link');
      clusterCss.rel = 'stylesheet';
      clusterCss.href = 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css';
      document.head.appendChild(clusterCss);

      const clusterDefaultCss = document.createElement('link');
      clusterDefaultCss.rel = 'stylesheet';
      clusterDefaultCss.href = 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css';
      document.head.appendChild(clusterDefaultCss);
    }

    // Load Leaflet JS first, then MarkerCluster
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
    script.crossOrigin = '';
    script.onload = () => {
      // Now load MarkerCluster plugin
      const clusterScript = document.createElement('script');
      clusterScript.src = 'https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js';
      clusterScript.onload = () => resolve(window.L);
      clusterScript.onerror = reject;
      document.head.appendChild(clusterScript);
    };
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

// Geocode an address using Nominatim (free OpenStreetMap geocoding)
async function geocodeAddress(address) {
  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(address)}&format=json&limit=1&countrycodes=us`;

  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': currentBrand.userAgent
      }
    });
    const data = await response.json();
    if (data && data.length > 0) {
      return {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon),
        display_name: data[0].display_name
      };
    }
  } catch (err) {
    console.error('Geocoding error:', err);
  }
  return null;
}

function TournamentMap({ tournaments, onFilteredTournaments }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const clusterGroupRef = useRef(null); // For marker clustering
  const userMarkerRef = useRef(null);
  const circleRef = useRef(null);
  const shouldFitBoundsRef = useRef(false); // Only fit bounds when explicitly requested

  const [leafletLoaded, setLeafletLoaded] = useState(false);
  const [userAddress, setUserAddress] = useState('');
  const [userLocation, setUserLocation] = useState(null);
  const [radius, setRadius] = useState(100);
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [geocodeError, setGeocodeError] = useState(null);
  const [showMap, setShowMap] = useState(false);

  // Load Leaflet on component mount
  useEffect(() => {
    loadLeaflet()
      .then(() => setLeafletLoaded(true))
      .catch(err => console.error('Failed to load Leaflet:', err));
  }, []);

  // Initialize map when Leaflet is loaded and map is shown
  useEffect(() => {
    if (!leafletLoaded || !showMap || !mapRef.current || mapInstanceRef.current) return;

    const L = window.L;

    // Center on USA
    const map = L.map(mapRef.current).setView([39.8283, -98.5795], 4);

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    mapInstanceRef.current = map;

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [leafletLoaded, showMap]);

  // Update markers when tournaments or user location changes
  const updateMarkers = useCallback(() => {
    if (!mapInstanceRef.current || !leafletLoaded) return;

    const L = window.L;
    const map = mapInstanceRef.current;

    // Clear existing cluster group and markers
    if (clusterGroupRef.current) {
      map.removeLayer(clusterGroupRef.current);
    }
    markersRef.current = [];

    // Create new cluster group with custom options
    clusterGroupRef.current = L.markerClusterGroup({
      showCoverageOnHover: false,
      maxClusterRadius: 50, // Cluster markers within 50 pixels
      spiderfyOnMaxZoom: true,
      disableClusteringAtZoom: 12, // Show individual markers at zoom 12+
      iconCreateFunction: function(cluster) {
        const count = cluster.getChildCount();
        return L.divIcon({
          html: `<div class="cluster-marker"><span>${count}</span></div>`,
          className: 'custom-cluster-icon',
          iconSize: [40, 40]
        });
      }
    });

    // Filter tournaments with coordinates
    const tournamentsWithCoords = tournaments.filter(t => t.latitude && t.longitude);

    // Calculate distances and filter by radius if user location is set
    let filteredTournaments = tournamentsWithCoords;
    if (userLocation) {
      filteredTournaments = tournamentsWithCoords.map(t => ({
        ...t,
        distance: calculateDistance(userLocation.lat, userLocation.lng, t.latitude, t.longitude)
      })).filter(t => t.distance <= radius);
    }

    // Group tournaments by exact coordinates to detect duplicates
    const coordGroups = {};
    filteredTournaments.forEach((tournament, index) => {
      const key = `${tournament.latitude.toFixed(6)},${tournament.longitude.toFixed(6)}`;
      if (!coordGroups[key]) {
        coordGroups[key] = [];
      }
      coordGroups[key].push({ tournament, index });
    });

    // Add numbered markers with offset for duplicates
    filteredTournaments.forEach((tournament, index) => {
      const markerNumber = index + 1;
      const key = `${tournament.latitude.toFixed(6)},${tournament.longitude.toFixed(6)}`;
      const group = coordGroups[key];

      // Calculate offset for tournaments at the same location
      let lat = tournament.latitude;
      let lng = tournament.longitude;

      if (group.length > 1) {
        // Find position in group
        const posInGroup = group.findIndex(g => g.index === index);
        const totalInGroup = group.length;

        // Spread in a circle pattern (radius ~0.002 degrees ≈ 200m)
        const radius = 0.002;
        const angle = (2 * Math.PI * posInGroup) / totalInGroup;
        lat = tournament.latitude + radius * Math.cos(angle);
        lng = tournament.longitude + radius * Math.sin(angle);
      }

      // Create custom numbered icon
      const numberedIcon = L.divIcon({
        className: 'numbered-marker',
        html: `<div class="marker-pin"><span>${markerNumber}</span></div>`,
        iconSize: [30, 40],
        iconAnchor: [15, 40],
        popupAnchor: [0, -35],
        tooltipAnchor: [0, -30]
      });

      const marker = L.marker([lat, lng], { icon: numberedIcon })
        .bindTooltip(tournament.name || 'Tournament', {
          permanent: false,
          direction: 'top',
          className: 'tournament-tooltip'
        })
        .bindPopup(`
          <strong>#${markerNumber}: ${tournament.name || 'Tournament'}</strong><br>
          ${tournament.city ? tournament.city + ', ' : ''}${tournament.state || ''}<br>
          ${tournament.dates || ''}<br>
          ${tournament.distance ? `<em>${tournament.distance.toFixed(1)} miles away</em>` : ''}
        `);

      clusterGroupRef.current.addLayer(marker);
      markersRef.current.push(marker);

      // Store the map number on the tournament object
      tournament.mapNumber = markerNumber;
    });

    // Add cluster group to map
    map.addLayer(clusterGroupRef.current);

    // Notify parent of filtered tournaments
    if (onFilteredTournaments) {
      onFilteredTournaments(filteredTournaments);
    }

    // Only fit bounds when explicitly requested (not on every update)
    if (shouldFitBoundsRef.current && markersRef.current.length > 0) {
      const group = L.featureGroup(markersRef.current);
      map.fitBounds(group.getBounds().pad(0.1));
      shouldFitBoundsRef.current = false; // Reset so user can freely zoom
    }
  }, [tournaments, userLocation, radius, leafletLoaded, onFilteredTournaments]);

  // Update markers when dependencies change
  useEffect(() => {
    if (showMap) {
      updateMarkers();
    }
  }, [showMap, updateMarkers]);

  // Update user marker and circle when location changes
  useEffect(() => {
    if (!mapInstanceRef.current || !leafletLoaded || !userLocation) return;

    const L = window.L;
    const map = mapInstanceRef.current;

    // Remove old user marker and circle
    if (userMarkerRef.current) userMarkerRef.current.remove();
    if (circleRef.current) circleRef.current.remove();

    // Add user marker (different color)
    const userIcon = L.divIcon({
      className: 'user-location-marker',
      html: '<div style="background: #2196F3; width: 16px; height: 16px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);"></div>',
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });

    userMarkerRef.current = L.marker([userLocation.lat, userLocation.lng], { icon: userIcon })
      .bindPopup('Your location')
      .addTo(map);

    // Add radius circle
    circleRef.current = L.circle([userLocation.lat, userLocation.lng], {
      radius: radius * 1609.34, // Convert miles to meters
      color: '#2196F3',
      fillColor: '#2196F3',
      fillOpacity: 0.1,
      weight: 2
    }).addTo(map);

    // Center on user location
    map.setView([userLocation.lat, userLocation.lng], 7);

  }, [userLocation, radius, leafletLoaded]);

  // Handle address search
  const handleSearch = async () => {
    if (!userAddress.trim()) return;

    setIsGeocoding(true);
    setGeocodeError(null);

    const result = await geocodeAddress(userAddress);

    if (result) {
      setUserLocation({ lat: result.lat, lng: result.lng });
      setGeocodeError(null);
      // Don't auto-fit bounds - the useEffect for userLocation will center on user
    } else {
      setGeocodeError('Could not find that address. Try adding city/state.');
    }

    setIsGeocoding(false);
  };

  // Handle clearing the filter
  const handleClear = () => {
    setUserAddress('');
    setUserLocation(null);
    setGeocodeError(null);

    if (userMarkerRef.current) {
      userMarkerRef.current.remove();
      userMarkerRef.current = null;
    }
    if (circleRef.current) {
      circleRef.current.remove();
      circleRef.current = null;
    }

    // Reset to show all tournaments
    if (onFilteredTournaments) {
      onFilteredTournaments(null);
    }

    // Reset map view
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([39.8283, -98.5795], 4);
      updateMarkers();
    }
  };

  // Handle "Fit All" button - manually fit map to show all visible markers
  const handleFitAll = () => {
    if (!mapInstanceRef.current || markersRef.current.length === 0) return;
    const L = window.L;
    const group = L.featureGroup(markersRef.current);
    mapInstanceRef.current.fitBounds(group.getBounds().pad(0.1));
  };

  // Get my location using browser geolocation
  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      setGeocodeError('Geolocation is not supported by your browser');
      return;
    }

    setIsGeocoding(true);
    setGeocodeError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude
        });
        setUserAddress('Current Location');
        setIsGeocoding(false);
      },
      (error) => {
        setGeocodeError('Unable to get your location. Please enter an address.');
        setIsGeocoding(false);
      }
    );
  };

  // Count tournaments with coordinates
  const tournamentsWithCoords = tournaments.filter(t => t.latitude && t.longitude).length;

  return (
    <div className="tournament-map-wrapper">
      <div className="map-toggle">
        <button
          className={`map-toggle-btn ${showMap ? 'active' : ''}`}
          onClick={() => setShowMap(!showMap)}
        >
          {showMap ? 'Hide Map' : 'Show Map'} ({tournamentsWithCoords} with locations)
        </button>
      </div>

      {showMap && (
        <div className="map-container">
          {/* Location Search */}
          <div className="map-controls">
            <div className="location-search">
              <input
                type="text"
                className="location-input"
                placeholder="Enter your address or zip code..."
                value={userAddress}
                onChange={(e) => setUserAddress(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button
                className="location-btn search-btn"
                onClick={handleSearch}
                disabled={isGeocoding || !userAddress.trim()}
              >
                {isGeocoding ? '...' : 'Search'}
              </button>
              <button
                className="location-btn my-location-btn"
                onClick={handleUseMyLocation}
                disabled={isGeocoding}
                title="Use my current location"
              >
                <TournamentIcon size={18} color="green" />
              </button>
            </div>

            <div className="radius-control">
              <label>Within:</label>
              <select
                className="radius-select"
                value={radius}
                onChange={(e) => setRadius(parseInt(e.target.value))}
              >
                <option value={25}>25 miles</option>
                <option value={50}>50 miles</option>
                <option value={100}>100 miles</option>
                <option value={200}>200 miles</option>
                <option value={500}>500 miles</option>
                <option value={1000}>1000 miles</option>
              </select>
              <button className="fit-all-btn" onClick={handleFitAll} title="Fit map to show all tournaments">
                Fit All
              </button>
              {userLocation && (
                <button className="clear-btn" onClick={handleClear}>
                  Clear
                </button>
              )}
            </div>
          </div>

          {geocodeError && (
            <div className="geocode-error">{geocodeError}</div>
          )}

          {/* Map */}
          <div ref={mapRef} className="map" />

          {userLocation && (
            <div className="map-info">
              Showing tournaments within {radius} miles of your location
            </div>
          )}
        </div>
      )}

      <style>{`
        .tournament-map-wrapper {
          margin-bottom: 1rem;
        }

        .map-toggle {
          margin-bottom: 0.5rem;
        }

        .map-toggle-btn {
          background: var(--primary-green);
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.9rem;
          font-weight: 500;
        }

        .map-toggle-btn:hover {
          background: var(--accent-green);
        }

        .map-toggle-btn.active {
          background: var(--accent-green);
        }

        .map-container {
          background: white;
          border-radius: 8px;
          padding: 1rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .map-controls {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          margin-bottom: 1rem;
          align-items: center;
        }

        .location-search {
          display: flex;
          gap: 0.5rem;
          flex: 1;
          min-width: 280px;
        }

        .location-input {
          flex: 1;
          padding: 0.5rem 0.75rem;
          border: 2px solid #e0e0e0;
          border-radius: 6px;
          font-size: 0.9rem;
        }

        .location-input:focus {
          outline: none;
          border-color: var(--accent-green);
        }

        .location-btn {
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.2s;
        }

        .search-btn {
          background: var(--primary-green);
          color: white;
        }

        .search-btn:hover:not(:disabled) {
          background: var(--accent-green);
        }

        .search-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .my-location-btn {
          background: #f0f0f0;
          font-size: 1rem;
          padding: 0.5rem 0.75rem;
        }

        .my-location-btn:hover:not(:disabled) {
          background: #e0e0e0;
        }

        .radius-control {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .radius-control label {
          font-size: 0.9rem;
          color: #666;
        }

        .radius-select {
          padding: 0.5rem 0.75rem;
          border: 2px solid #e0e0e0;
          border-radius: 6px;
          font-size: 0.9rem;
          background: white;
        }

        .clear-btn,
        .fit-all-btn {
          background: #f5f5f5;
          color: #666;
          border: none;
          padding: 0.5rem 0.75rem;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.85rem;
        }

        .clear-btn:hover,
        .fit-all-btn:hover {
          background: #e0e0e0;
        }

        .geocode-error {
          background: #fff3f3;
          color: #c62828;
          padding: 0.5rem 1rem;
          border-radius: 6px;
          margin-bottom: 1rem;
          font-size: 0.9rem;
        }

        .map {
          height: 400px;
          border-radius: 8px;
          z-index: 1;
        }

        /* Numbered marker pins */
        .numbered-marker {
          background: transparent;
          border: none;
        }

        .marker-pin {
          width: 30px;
          height: 40px;
          position: relative;
          background: var(--primary-green, #2d5a27);
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }

        .marker-pin span {
          transform: rotate(45deg);
          color: white;
          font-weight: bold;
          font-size: 12px;
        }

        /* Tooltip styling */
        .tournament-tooltip {
          background: white;
          border: 1px solid #ccc;
          border-radius: 4px;
          padding: 4px 8px;
          font-size: 12px;
          font-weight: 500;
          box-shadow: 0 2px 8px rgba(0,0,0,0.15);
          white-space: nowrap;
          max-width: 250px;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .tournament-tooltip::before {
          border-top-color: white;
        }

        /* Cluster marker styling */
        .custom-cluster-icon {
          background: transparent;
        }

        .cluster-marker {
          width: 40px;
          height: 40px;
          background: var(--primary-green, #2d5a27);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 3px 8px rgba(0,0,0,0.3);
          border: 3px solid white;
        }

        .cluster-marker span {
          color: white;
          font-weight: bold;
          font-size: 14px;
        }

        .map-info {
          margin-top: 0.75rem;
          padding: 0.5rem;
          background: #e8f5e9;
          border-radius: 6px;
          font-size: 0.85rem;
          color: var(--primary-green);
          text-align: center;
        }

        @media (max-width: 768px) {
          .map-controls {
            flex-direction: column;
            align-items: stretch;
          }

          .location-search {
            min-width: 100%;
          }

          .radius-control {
            justify-content: space-between;
          }

          .map {
            height: 300px;
          }
        }

        @media (max-width: 480px) {
          .location-search {
            flex-wrap: wrap;
          }

          .location-input {
            width: 100%;
            min-width: 100%;
          }

          .location-btn {
            flex: 1;
          }

          .map {
            height: 250px;
          }
        }
      `}</style>
    </div>
  );
}

export default TournamentMap;
