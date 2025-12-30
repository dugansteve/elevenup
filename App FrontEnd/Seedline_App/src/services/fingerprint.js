/**
 * Device Fingerprinting Service
 *
 * Collects browser and device information for:
 * - Session tracking across visits
 * - Suspicious behavior detection
 * - Analytics and debugging
 */

/**
 * Collect all available device fingerprint data
 */
export async function collectFingerprint() {
  const fingerprint = {
    // Basic browser info
    userAgent: navigator.userAgent,
    language: navigator.language,
    languages: navigator.languages ? [...navigator.languages] : [navigator.language],
    platform: navigator.platform,
    vendor: navigator.vendor || '',

    // Screen info
    screenWidth: screen.width,
    screenHeight: screen.height,
    colorDepth: screen.colorDepth,
    pixelRatio: window.devicePixelRatio || 1,

    // Time info
    timezone: getTimezone(),
    timezoneOffset: new Date().getTimezoneOffset(),

    // Browser features
    cookiesEnabled: navigator.cookieEnabled,
    doNotTrack: navigator.doNotTrack || 'unspecified',

    // Hardware hints
    hardwareConcurrency: navigator.hardwareConcurrency || 0,
    maxTouchPoints: navigator.maxTouchPoints || 0,

    // Device memory (if available)
    deviceMemory: navigator.deviceMemory || null,
  };

  // Generate hash for comparison
  fingerprint.hash = await hashFingerprint(fingerprint);

  return fingerprint;
}

/**
 * Get timezone string
 */
function getTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return 'Unknown';
  }
}

/**
 * Generate SHA-256 hash of fingerprint data
 */
async function hashFingerprint(data) {
  try {
    // Create a consistent string representation
    const str = JSON.stringify({
      userAgent: data.userAgent,
      screen: `${data.screenWidth}x${data.screenHeight}`,
      colorDepth: data.colorDepth,
      timezone: data.timezone,
      language: data.language,
      platform: data.platform,
    });

    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(str);
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  } catch {
    // Fallback for browsers without crypto.subtle
    return simpleHash(JSON.stringify(data));
  }
}

/**
 * Simple fallback hash function
 */
function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(16).padStart(8, '0');
}

/**
 * Check if the browser appears to be a bot/scraper
 */
export function detectBot() {
  const indicators = {
    // No plugins (common for headless browsers)
    noPlugins: navigator.plugins.length === 0,

    // Webdriver flag (Selenium, Puppeteer)
    webdriver: navigator.webdriver === true,

    // Missing language
    noLanguage: !navigator.language,

    // Suspicious user agent
    suspiciousUA: /bot|crawl|spider|scrape|headless|phantom/i.test(navigator.userAgent),

    // Screen size is 0 (headless)
    zeroScreen: screen.width === 0 || screen.height === 0,

    // Missing features typical of bots
    missingFeatures: typeof window.chrome === 'undefined' &&
                     typeof window.opera === 'undefined' &&
                     typeof window.safari === 'undefined',
  };

  const score = Object.values(indicators).filter(Boolean).length;

  return {
    isLikelyBot: score >= 2,
    score,
    indicators,
  };
}

/**
 * Get device type (mobile, tablet, desktop)
 */
export function getDeviceType() {
  const ua = navigator.userAgent;

  if (/tablet|ipad|playbook|silk/i.test(ua)) {
    return 'tablet';
  }

  if (/mobile|iphone|ipod|android|blackberry|opera mini|iemobile/i.test(ua)) {
    return 'mobile';
  }

  return 'desktop';
}

/**
 * Get browser name and version
 */
export function getBrowser() {
  const ua = navigator.userAgent;
  let browser = 'Unknown';
  let version = '';

  if (ua.indexOf('Firefox') > -1) {
    browser = 'Firefox';
    version = ua.match(/Firefox\/(\d+)/)?.[1] || '';
  } else if (ua.indexOf('Opera') > -1 || ua.indexOf('OPR') > -1) {
    browser = 'Opera';
    version = ua.match(/(?:Opera|OPR)\/(\d+)/)?.[1] || '';
  } else if (ua.indexOf('Edg') > -1) {
    browser = 'Edge';
    version = ua.match(/Edg\/(\d+)/)?.[1] || '';
  } else if (ua.indexOf('Chrome') > -1) {
    browser = 'Chrome';
    version = ua.match(/Chrome\/(\d+)/)?.[1] || '';
  } else if (ua.indexOf('Safari') > -1) {
    browser = 'Safari';
    version = ua.match(/Version\/(\d+)/)?.[1] || '';
  } else if (ua.indexOf('MSIE') > -1 || ua.indexOf('Trident') > -1) {
    browser = 'Internet Explorer';
    version = ua.match(/(?:MSIE |rv:)(\d+)/)?.[1] || '';
  }

  return { browser, version };
}

/**
 * Get operating system
 */
export function getOS() {
  const ua = navigator.userAgent;

  if (ua.indexOf('Win') > -1) return 'Windows';
  if (ua.indexOf('Mac') > -1) return 'macOS';
  if (ua.indexOf('Linux') > -1) return 'Linux';
  if (ua.indexOf('Android') > -1) return 'Android';
  if (ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) return 'iOS';

  return 'Unknown';
}
