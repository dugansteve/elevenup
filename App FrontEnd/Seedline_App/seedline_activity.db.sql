-- Seedline Activity Logging Database Schema
-- Separate from main seedlinedata.db for performance and maintainability

-- Sessions table - one per browser session
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,                        -- Firebase UID or NULL for guests
    firebase_uid TEXT,                   -- Firebase UID if authenticated
    account_type TEXT DEFAULT 'guest',   -- guest, free, paid, coach, admin

    -- Device fingerprint
    ip_address TEXT,
    user_agent TEXT,
    screen_width INTEGER,
    screen_height INTEGER,
    color_depth INTEGER,
    pixel_ratio REAL,
    timezone TEXT,
    timezone_offset INTEGER,
    language TEXT,
    languages TEXT,                      -- JSON array
    platform TEXT,                       -- win32, darwin, linux, android, ios
    vendor TEXT,
    hardware_concurrency INTEGER,
    max_touch_points INTEGER,
    cookies_enabled INTEGER,
    do_not_track TEXT,
    fingerprint_hash TEXT,               -- SHA-256 of fingerprint for cross-session tracking

    -- Session metadata
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_activity TEXT DEFAULT (datetime('now')),
    page_view_count INTEGER DEFAULT 0,
    api_call_count INTEGER DEFAULT 0,

    -- Suspicious flags
    is_suspicious INTEGER DEFAULT 0,
    suspicious_reason TEXT,
    is_blocked INTEGER DEFAULT 0,
    blocked_reason TEXT,
    blocked_at TEXT,

    -- Referrer tracking
    referrer TEXT,
    landing_page TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_term TEXT,
    utm_content TEXT,

    -- IP geolocation and VPN detection
    ip_country TEXT,
    ip_region TEXT,
    ip_city TEXT,
    ip_isp TEXT,
    ip_org TEXT,
    ip_asn TEXT,
    is_vpn INTEGER,                      -- 1 = VPN detected, 0 = no VPN, NULL = unknown
    is_proxy INTEGER,
    is_hosting INTEGER,                  -- Datacenter/hosting provider IP
    is_mobile INTEGER
);

-- Page views table - every page visit
CREATE TABLE IF NOT EXISTS page_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id TEXT,

    -- Page details
    page_type TEXT NOT NULL,             -- rankings, team, club, player, badges, settings, etc.
    page_path TEXT NOT NULL,             -- /team/123, /club/SoCal%20Blues
    page_params TEXT,                    -- JSON of query params

    -- Entity tracking (for team/club/player pages)
    entity_type TEXT,                    -- team, club, player
    entity_id TEXT,                      -- numeric ID or URL-encoded name
    entity_name TEXT,                    -- Human-readable name

    -- Timing
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    time_on_page_ms INTEGER,             -- Updated when user leaves page

    -- Navigation context
    previous_page TEXT,
    previous_entity_id TEXT,             -- For detecting sequential browsing
    navigation_method TEXT,              -- click, direct, back, forward, search, external

    -- Scroll depth tracking
    max_scroll_depth INTEGER,            -- Percentage 0-100

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- API calls table (for tracking data requests)
CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_id TEXT,
    ip_address TEXT,

    -- Request details
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    params TEXT,                         -- JSON
    headers TEXT,                        -- JSON (selected headers)

    -- Response
    status_code INTEGER,
    response_time_ms INTEGER,
    response_size_bytes INTEGER,
    error_message TEXT,

    -- Rate limiting
    was_rate_limited INTEGER DEFAULT 0,

    timestamp TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Suspicious activity flags
CREATE TABLE IF NOT EXISTS suspicious_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_id TEXT,
    ip_address TEXT,
    fingerprint_hash TEXT,

    -- Detection
    detection_type TEXT NOT NULL,        -- rate_limit, sequential_browsing, rapid_navigation, high_volume, pattern_match
    detection_rule TEXT,                 -- e.g., "team_pages_per_day > 100"
    severity TEXT NOT NULL,              -- low, medium, high, critical

    -- Context
    details TEXT,                        -- JSON with specific details
    page_views_count INTEGER,            -- Count at time of detection
    api_calls_count INTEGER,

    timestamp TEXT NOT NULL DEFAULT (datetime('now')),

    -- Resolution
    resolved INTEGER DEFAULT 0,
    resolved_at TEXT,
    resolved_by TEXT,
    resolution_notes TEXT,
    action_taken TEXT,                   -- none, warned, throttled, blocked

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Daily aggregates for quick lookups
CREATE TABLE IF NOT EXISTS daily_session_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                  -- YYYY-MM-DD
    session_id TEXT NOT NULL,
    user_id TEXT,
    ip_address TEXT,
    fingerprint_hash TEXT,

    -- Counts
    page_views INTEGER DEFAULT 0,
    team_pages INTEGER DEFAULT 0,
    club_pages INTEGER DEFAULT 0,
    player_pages INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,

    -- Patterns
    unique_teams_viewed INTEGER DEFAULT 0,
    sequential_team_views INTEGER DEFAULT 0,  -- Count of sequential ID patterns
    max_pages_per_minute REAL DEFAULT 0,

    -- Flags
    flagged INTEGER DEFAULT 0,
    flag_reasons TEXT,                   -- JSON array

    UNIQUE(date, session_id)
);

-- Blocked IPs and fingerprints
CREATE TABLE IF NOT EXISTS blocklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_type TEXT NOT NULL,            -- ip, fingerprint, user_id
    block_value TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT,                     -- NULL = permanent
    created_by TEXT,
    is_active INTEGER DEFAULT 1,

    UNIQUE(block_type, block_value)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_ip ON sessions(ip_address);
CREATE INDEX IF NOT EXISTS idx_sessions_fingerprint ON sessions(fingerprint_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_suspicious ON sessions(is_suspicious);

CREATE INDEX IF NOT EXISTS idx_pageviews_session ON page_views(session_id);
CREATE INDEX IF NOT EXISTS idx_pageviews_timestamp ON page_views(timestamp);
CREATE INDEX IF NOT EXISTS idx_pageviews_entity ON page_views(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_pageviews_type ON page_views(page_type);
CREATE INDEX IF NOT EXISTS idx_pageviews_date ON page_views(date(timestamp));

CREATE INDEX IF NOT EXISTS idx_api_session ON api_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_api_endpoint ON api_calls(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_timestamp ON api_calls(timestamp);
CREATE INDEX IF NOT EXISTS idx_api_ip ON api_calls(ip_address);

CREATE INDEX IF NOT EXISTS idx_suspicious_session ON suspicious_activity(session_id);
CREATE INDEX IF NOT EXISTS idx_suspicious_ip ON suspicious_activity(ip_address);
CREATE INDEX IF NOT EXISTS idx_suspicious_severity ON suspicious_activity(severity);
CREATE INDEX IF NOT EXISTS idx_suspicious_unresolved ON suspicious_activity(resolved, severity);

CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_session_stats(date);
CREATE INDEX IF NOT EXISTS idx_daily_session ON daily_session_stats(session_id);
CREATE INDEX IF NOT EXISTS idx_daily_ip ON daily_session_stats(ip_address);

CREATE INDEX IF NOT EXISTS idx_blocklist_active ON blocklist(block_type, block_value, is_active);

-- ============================================================================
-- TEAM RATINGS TABLE - User-submitted team reviews with Claude moderation
-- ============================================================================

CREATE TABLE IF NOT EXISTS team_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Team identification (matches rankings JSON format)
    team_id INTEGER NOT NULL,                -- Numeric team ID from rankings
    team_name TEXT NOT NULL,                 -- Team name for display/backup
    team_age_group TEXT,                     -- e.g., G12, B11
    team_league TEXT,                        -- e.g., ECNL, GA

    -- Reviewer identification
    user_id TEXT NOT NULL,                   -- Firebase UID
    session_id TEXT,                         -- Session for tracking

    -- Relationship to team: 'my_team', 'followed', 'neither'
    relationship TEXT NOT NULL DEFAULT 'neither',

    -- Required comment (moderated by Claude)
    comment TEXT NOT NULL,                   -- Must be non-empty, 10-1000 chars

    -- Optional category ratings (1-5 scale, NULL if not rated)
    rating_possession INTEGER CHECK (rating_possession IS NULL OR rating_possession BETWEEN 1 AND 5),
    rating_direct_attack INTEGER CHECK (rating_direct_attack IS NULL OR rating_direct_attack BETWEEN 1 AND 5),
    rating_passing INTEGER CHECK (rating_passing IS NULL OR rating_passing BETWEEN 1 AND 5),
    rating_fast INTEGER CHECK (rating_fast IS NULL OR rating_fast BETWEEN 1 AND 5),
    rating_shooting INTEGER CHECK (rating_shooting IS NULL OR rating_shooting BETWEEN 1 AND 5),
    rating_footwork INTEGER CHECK (rating_footwork IS NULL OR rating_footwork BETWEEN 1 AND 5),
    rating_physical INTEGER CHECK (rating_physical IS NULL OR rating_physical BETWEEN 1 AND 5),
    rating_coaching INTEGER CHECK (rating_coaching IS NULL OR rating_coaching BETWEEN 1 AND 5),
    rating_allstar_players INTEGER CHECK (rating_allstar_players IS NULL OR rating_allstar_players BETWEEN 1 AND 5),
    rating_player_sportsmanship INTEGER CHECK (rating_player_sportsmanship IS NULL OR rating_player_sportsmanship BETWEEN 1 AND 5),
    rating_parent_sportsmanship INTEGER CHECK (rating_parent_sportsmanship IS NULL OR rating_parent_sportsmanship BETWEEN 1 AND 5),
    rating_strong_defense INTEGER CHECK (rating_strong_defense IS NULL OR rating_strong_defense BETWEEN 1 AND 5),
    rating_strong_midfield INTEGER CHECK (rating_strong_midfield IS NULL OR rating_strong_midfield BETWEEN 1 AND 5),
    rating_strong_offense INTEGER CHECK (rating_strong_offense IS NULL OR rating_strong_offense BETWEEN 1 AND 5),

    -- Moderation status: 'pending', 'approved', 'rejected'
    moderation_status TEXT DEFAULT 'pending',
    moderation_reason TEXT,                   -- Rejection reason if rejected
    moderated_at TEXT,

    -- Timestamps
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),

    -- Soft delete
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Indexes for team_ratings performance
CREATE INDEX IF NOT EXISTS idx_ratings_team ON team_ratings(team_id);
CREATE INDEX IF NOT EXISTS idx_ratings_user ON team_ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_ratings_status ON team_ratings(moderation_status);
CREATE INDEX IF NOT EXISTS idx_ratings_created ON team_ratings(created_at);

-- Composite index for fetching approved ratings for a team
CREATE INDEX IF NOT EXISTS idx_ratings_team_approved ON team_ratings(team_id, moderation_status, is_deleted);

-- Unique constraint: one active rating per user per team
CREATE UNIQUE INDEX IF NOT EXISTS idx_ratings_user_team_unique ON team_ratings(user_id, team_id)
    WHERE is_deleted = 0;
