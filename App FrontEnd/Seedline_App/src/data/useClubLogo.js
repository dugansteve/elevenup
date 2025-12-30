import { useState, useEffect } from 'react';

// Cache for the logo lookup data
let logoLookupCache = null;
let loadingPromise = null;

// Additional hardcoded mappings for clubs with different naming conventions
// IMPORTANT: Only use specific club names to avoid false matches
const ADDITIONAL_MAPPINGS = {
  // Albion Hurricanes FC - ECNL club based in Houston
  'albion hurricanes fc': 'Albion_Hurricanes_logo.png',
  'albion hurricanes': 'Albion_Hurricanes_logo.png',

  // Beach Futbol Club - California
  'beach futbol club': 'Beach_FC_CA_logo.jpeg',

  // Slammers FC - California ECNL club
  'slammers fc': 'SLAMMERS_FC_logo.png',
  'cda slammers': 'SLAMMERS_FC_logo.png',
  'slammers fc hb koge': 'Slammers_FC_HB_Koge_logo.png',

  // Rebels Soccer Club - California 1982
  'rebels soccer club': 'Rebels_SC_logo.png',

  // FC Dallas Youth
  'fc dallas': 'FC_Dallas_logo.png',
  'fc dallas youth': 'FC_Dallas_logo.png',

  // Solar Soccer Club - Dallas TX
  'solar sc': 'SOLAR_BLUE_logo.png',
  'solar soccer club': 'SOLAR_BLUE_logo.png',

  // Concorde Fire - Atlanta
  'concorde fire': 'Concorde_Fire_logo.jpeg',
  'concorde fire platinum': 'Concorde_Fire_logo.jpeg',
  'atlanta concorde fire': 'Concorde_Fire_logo.jpeg',

  // GSA - Georgia Soccer Academy
  'georgia soccer academy': 'GSA_logo.jpeg',

  // Dallas Texans
  'dallas texans': 'Dallas_Texans_logo.jpeg',

  // Rush clubs - SPECIFIC mappings only
  'colorado rush': 'Colorado_Rush_Academy_logo.png',
  'colorado rush soccer club': 'Colorado_Rush_Academy_logo.png',
  'idaho rush': 'Idaho_Rush_logo.jpeg',
  'kansas rush': 'Kansas_Rush_logo.png',

  // Surf clubs - SPECIFIC mappings only
  'dallas surf': 'Dallas_Surf_logo.png',
  'utah surf': 'Utah_Surf_logo.png',

  // SLSG - St Louis Scott Gallagher
  'st louis scott gallagher': 'SLSG_logo.png',
  'slsg': 'SLSG_logo.png',

  // PSA - Players Soccer Academy (specific)
  'psa': 'PSA_logo.png',
  'psa north': 'PSA_North_logo.png',

  // Real Colorado
  'real colorado': 'Real_Colorado_logo.jpeg',

  // Sporting clubs - SPECIFIC only
  'sporting kansas city': 'Sporting_Kansas_City_logo.jpeg',
  'sporting kc': 'Sporting_Kansas_City_logo.jpeg',
  'sporting iowa': 'Sporting_Iowa_logo.png',
  'sporting springfield': 'Sporting_Springfield_logo.png',
  'sporting blue valley': 'Sporting_logo.jpeg',

  // Utah Avalanche - SPECIFIC
  'utah avalanche': 'Utah_Avalanche_logo.png',

  // Colorado Rapids
  'colorado rapids': 'Colorado_Rapids_Central_logo.png',
  'colorado rapids youth': 'Colorado_Rapids_Central_logo.png',

  // Phoenix Rising
  'phoenix rising': 'Phoenix_Rising_logo.png',
  'phoenix rising fc': 'Phoenix_Rising_logo.png',

  // Livermore Fusion
  'livermore fusion': 'Livermore_Fusion_SC_logo.jpeg',
  'livermore fusion sc': 'Livermore_Fusion_SC_logo.jpeg',

  // La Roca FC
  'la roca fc': 'La_Roca_FC_logo.jpeg',
  'la roca': 'La_Roca_FC_logo.jpeg',

  // Racing Louisville
  'racing louisville': 'Racing_Louisville_Academy_logo.jpeg',
  'racing louisville academy': 'Racing_Louisville_Academy_logo.jpeg',

  // Tennessee SC
  'tennessee soccer club': 'Tennessee_SC_logo.jpeg',
  'tennessee sc': 'Tennessee_SC_logo.jpeg',

  // Wilmington Hammerheads
  'wilmington hammerheads': 'Wilmington_Hammerheads_logo.png',

  // Eastside Timbers - Oregon
  'eastside timbers fc': 'Eastside_Timbers_logo.png',
  'eastside timbers': 'Eastside_Timbers_logo.png',

  // Boise Thorns/Timbers
  'boise thorns fc': 'Boise_Thorns_FC_logo.png',
  'boise timbers thorns fc': 'Boise_Thorns_FC_logo.png',

  // Arsenal Colorado
  'arsenal colorado': 'Arsenal_Colorado_logo.png',

  // City SC Utah - SPECIFIC (not Orlando City, not other City clubs)
  'city sc utah': 'City_SC_Utah_logo.png',

  // Pittsburgh Riverhounds
  'pittsburgh riverhounds': 'Pittsburgh_Riverhounds_logo.png',

  // World Class FC
  'world class fc': 'World_Class_FC_logo.png',

  // SUSA FC
  'susa fc': 'SUSA_FC_logo.png',

  // Charlotte Soccer Academy
  'charlotte soccer academy': 'Charlotte_SA_Gold_logo.jpeg',
  'charlotte sa': 'Charlotte_SA_Gold_logo.jpeg',

  // NC Fusion
  'nc fusion': 'NC_Fusion_logo.png',

  // FC Stars of Mass
  'fc stars': 'FC_Stars_logo.png',
  'fc stars of mass': 'FC_Stars_logo.png',

  // United Futbol Academy - Georgia (SPECIFIC, not generic United)
  'united futbol academy': 'United_logo.png',

  // Force New York (SPECIFIC, not generic Force)
  'force sc new york': 'Force_logo.png',
  'force new york': 'Force_logo.png',

  // South Carolina United FC (SPECIFIC, not generic South)
  'south carolina united': 'South_logo.jpeg',
  'south carolina united fc': 'South_logo.jpeg',

  // Mercury Soccer
  'mercury soccer': 'Mercury_logo.png',

  // Scorpions Soccer - San Antonio area
  'scorpions sc': 'Scorpions_logo.png',
  'scorpions soccer': 'Scorpions_logo.png',

  // Evolution Soccer
  'evolution sc': 'Evolution_logo.png',
  'evolution soccer': 'Evolution_logo.png',

  // Alabama FC
  'alabama fc': 'Alabama_FC_logo.png',

  // NCFC Youth
  'ncfc youth': 'NCFC_Youth_logo.png',

  // AC Connecticut
  'ac connecticut': 'AC_Connecticut_logo.jpeg',

  // Connecticut FC
  'connecticut fc': 'Connecticut_FC_logo.jpeg',

  // Gulf Coast Soccer Club
  'gulf coast soccer club': 'Gulf_Coast_logo.jpeg',
  'gulf coast sc': 'Gulf_Coast_logo.jpeg',

  // Bethesda SC
  'bethesda sc': 'Bethesda_SC_logo.png',

  // BRYC Academy
  'bryc': 'BRYC_Academy_logo.png',
  'bryc academy': 'BRYC_Academy_logo.png',

  // BVB IA
  'bvb ia': 'BVBIA_logo.png',
  'bvbia': 'BVBIA_logo.png',

  // Colorado EDGE
  'colorado edge': 'Colorado_EDGE_logo.png',

  // Highland FC
  'highland fc': 'Highland_FC_logo.png',

  // Hex FC
  'hex fc': 'HEX_FC_logo.png',

  // Liverpool FC IA
  'liverpool fc ia': 'Liverpool_FC_IA_GMA_logo.jpeg',

  // Manhattan SC
  'manhattan sc': 'Manhattan_SC_logo.png',

  // PWSI - Prince William Soccer Inc
  'pwsi': 'PWSI_logo.png',
  'prince william soccer': 'PWSI_logo.png',

  // Vienna Youth Soccer
  'vienna youth soccer': 'Vienna_logo.png',

  // West Mont United
  'west mont united': 'West_Mont_United_logo.png',
  'west mont united sa': 'West_Mont_United_logo.png',

  // FC Copa Academy
  'fc copa academy': 'FC_Copa_Academy_logo.png',
  'fc copa': 'FC_Copa_Academy_logo.png',

  // FSA FC
  'fsa fc': 'FSA_FC_logo.png',

  // Great Falls Reston Soccer
  'great falls reston soccer': 'Great_Falls_Reston_Soccer_logo.png',
  'gfrsc': 'Great_Falls_Reston_Soccer_logo.png',

  // Rockford Raptors
  'rockford raptors': 'Rockford_Raptors_logo.jpeg',

  // Stanford Strikers
  'stanford strikers': 'Stanford_Strikers_logo.png',

  // Sting Nebraska
  'sting nebraska': 'Sting_Nebraska_logo.png',

  // Texoma Soccer Academy
  'texoma soccer academy': 'Texoma_Soccer_Academy_logo.png',

  // State-named files that are actually specific clubs:
  // Indiana_logo.png = Indiana Elite
  'indiana elite': 'Indiana_logo.png',

  // Ohio_logo.png = Ohio Premier Soccer Club
  'ohio premier': 'Ohio_logo.png',
  'ohio premier soccer club': 'Ohio_logo.png',

  // Michigan_logo.png = Michigan Burn
  'michigan burn': 'Michigan_logo.png',

  // Missouri_logo.png = Missouri Rush
  'missouri rush': 'Missouri_logo.png',
  'missouri rush soccer club': 'Missouri_logo.png',

  // Mississippi_logo.png = Mississippi Rush Soccer Club
  'mississippi rush': 'Mississippi_logo.png',
  'mississippi rush soccer club': 'Mississippi_logo.png',

  // Seattle_logo.jpeg = Seattle United
  'seattle united': 'Seattle_logo.jpeg',

  // Philadelphia_logo.png = Philadelphia Ukrainian Nationals
  'philadelphia ukrainian nationals': 'Philadelphia_logo.png',

  // Utah_logo.png is MISLABELED - it's actually Royals Arizona
  'royals arizona': 'Utah_logo.png',

  // Pateadores
  'pateadores': 'Pateadores_logo.png',
  'pateadores soccer club': 'Pateadores_logo.png',

  // Reading Rage Surf
  'reading rage': 'Reading_Rage_Surf_logo.png',
  'reading rage surf': 'Reading_Rage_Surf_logo.png',

  // Pride SC
  'pride sc': 'Pride_SC_logo.png',
  'pride soccer club': 'Pride_SC_logo.png',

  // Plymouth Reign SC
  'plymouth reign sc': 'Plymouth_Reign_SC_logo.jpeg',
  'plymouth reign': 'Plymouth_Reign_SC_logo.jpeg',

  // NTX Celtic FC
  'ntx celtic fc': 'NTX_Celtic_FC_Green_logo.jpeg',
  'ntx celtic': 'NTX_Celtic_FC_Green_logo.jpeg',

  // NLSA
  'nlsa': 'NLSA_logo.png',

  // Kernow Storm FC
  'kernow storm fc': 'Kernow_Storm_FC_logo.png',
  'kernow storm': 'Kernow_Storm_FC_logo.png',

  // Eagles SC
  'eagles sc': 'Eagles_SC_logo.png',

  // Dallas Cosmos SC
  'dallas cosmos sc': 'Dallas_Cosmos_SC_logo.png',
  'dallas cosmos': 'Dallas_Cosmos_SC_logo.png',

  // Coastal Rush
  'coastal rush': 'Coastal_Rush_logo.png',

  // DKSC - Dallas Kicks SC
  'dksc': 'DKSC_WHITE_logo.jpeg',
  'dallas kicks sc': 'DKSC_WHITE_logo.jpeg',

  // Boerne SC
  'boerne sc': 'Boerne_SC_logo.png',

  // Arizona Arsenal
  'arizona arsenal': 'Arizona_Arsenal_logo.jpeg',

  // Arlington Soccer Association
  'arlington soccer association': 'Arlington_Soccer_logo.png',
  'arlington sa': 'Arlington_Soccer_logo.png',

  // Atletico Dallas Youth
  'atletico dallas youth': 'Atlético_Dallas_Youth_logo.png',
  'atletico dallas': 'Atlético_Dallas_Youth_logo.png',

  // Avanti Soccer Academy (SA)
  'avanti soccer academy': 'Avanti_SA_logo.png',
  'avanti sa': 'Avanti_SA_logo.png',

  // Beach FC Virginia (different from CA)
  'beach fc va': 'Beach_FC_VA_logo.png',
  'beach fc virginia': 'Beach_FC_VA_logo.png',

  // Chattanooga FC
  'chattanooga fc': 'Chattanooga_logo.jpeg',
  'chattanooga': 'Chattanooga_logo.jpeg',

  // CESA Liberty
  'cesa liberty': 'CESA_Liberty_logo.jpeg',
  'cesa': 'CESA_Liberty_logo.jpeg',

  // Albany Alleycats
  'albany alleycats': 'Albany_Alleycats_logo.jpeg',

  // Association Football Club
  'association football club': 'Association_FC_logo.png',

  // PDA South
  'pda south': 'PDA_SOUTH_WHITE_logo.jpeg',

  // Rush Select
  'rush select': 'Rush_Select_logo.jpeg',

  // ===== NEWLY DOWNLOADED LOGOS =====

  // Legends FC - California
  'legends fc': 'Legends_FC_logo.png',

  // LAFC So Cal Youth
  'lafc so cal youth': 'LAFC_So_Cal_Youth_logo.jpg',
  'lafc socal youth': 'LAFC_So_Cal_Youth_logo.jpg',
  'real so cal': 'LAFC_So_Cal_Youth_logo.jpg',

  // Beadling SC - Pittsburgh
  'beadling sc': 'Beadling_SC_logo.png',
  'beadling': 'Beadling_SC_logo.png',

  // Total Futbol Academy
  'total futbol academy': 'Total_Futbol_Academy_logo.jpg',
  'total futbol': 'Total_Futbol_Academy_logo.jpg',

  // California Football Academy
  'california football academy': 'California_Football_Academy_logo.png',
  'california football': 'California_Football_Academy_logo.png',

  // MLS Club Youth Programs
  'orlando city': 'Orlando_City_logo.svg',
  'orlando city sc': 'Orlando_City_logo.svg',
  'orlando city youth': 'Orlando_City_logo.svg',

  'austin fc': 'Austin_FC_logo.svg',
  'austin fc academy': 'Austin_FC_logo.svg',

  'fc cincinnati': 'FC_Cincinnati_logo.svg',
  'fc cincinnati academy': 'FC_Cincinnati_logo.svg',

  'charlotte fc': 'Charlotte_FC_logo.svg',
  'charlotte fc academy': 'Charlotte_FC_logo.svg',

  'inter miami': 'Inter_Miami_logo.svg',
  'inter miami cf': 'Inter_Miami_logo.svg',
  'inter miami academy': 'Inter_Miami_logo.svg',

  'nashville sc': 'Nashville_SC_logo.svg',
  'nashville sc academy': 'Nashville_SC_logo.svg',

  'st louis city': 'St_Louis_City_logo.svg',
  'st louis city sc': 'St_Louis_City_logo.svg',

  'atlanta united': 'Atlanta_United_logo.svg',
  'atlanta united fc': 'Atlanta_United_logo.svg',

  'houston dynamo': 'Houston_Dynamo_logo.svg',
  'houston dynamo fc': 'Houston_Dynamo_logo.svg',

  'san jose earthquakes': 'San_Jose_Earthquakes_logo.svg',
  'sj earthquakes': 'San_Jose_Earthquakes_logo.svg',

  'la galaxy': 'LA_Galaxy_logo.svg',
  'la galaxy academy': 'LA_Galaxy_logo.svg',

  'new york red bulls': 'New_York_Red_Bulls_logo.svg',
  'ny red bulls': 'New_York_Red_Bulls_logo.svg',
  'red bulls': 'New_York_Red_Bulls_logo.svg',

  'philadelphia union': 'Philadelphia_Union_logo.svg',
  'philly union': 'Philadelphia_Union_logo.svg',

  'portland timbers': 'Portland_Timbers_logo.svg',
  'portland timbers academy': 'Portland_Timbers_logo.svg',

  'seattle sounders': 'Seattle_Sounders_logo.svg',
  'seattle sounders fc': 'Seattle_Sounders_logo.svg',

  'columbus crew': 'Columbus_Crew_logo.svg',
  'columbus crew academy': 'Columbus_Crew_logo.svg',

  'dc united': 'DC_United_logo.svg',
  'dc united academy': 'DC_United_logo.svg',

  'minnesota united': 'Minnesota_United_logo.svg',
  'minnesota united fc': 'Minnesota_United_logo.svg',

  'real salt lake': 'Real_Salt_Lake_logo.svg',
  'rsl': 'Real_Salt_Lake_logo.svg',
  'real salt lake academy': 'Real_Salt_Lake_logo.svg',

  'vancouver whitecaps': 'Vancouver_Whitecaps_logo.svg',
  'vancouver whitecaps fc': 'Vancouver_Whitecaps_logo.svg',

  'toronto fc': 'Toronto_FC_logo.svg',
  'toronto fc academy': 'Toronto_FC_logo.svg',

  'cf montreal': 'CF_Montreal_logo.svg',
  'club de foot montreal': 'CF_Montreal_logo.svg',

  'new england revolution': 'New_England_Revolution_logo.svg',
  'ne revolution': 'New_England_Revolution_logo.svg',

  'chicago fire': 'Chicago_Fire_logo.svg',
  'chicago fire fc': 'Chicago_Fire_logo.svg',

  // Santa Barbara SC
  'santa barbara sc': 'Santa_Barbara_SC_logo.png',
  'santa barbara soccer club': 'Santa_Barbara_SC_logo.png',

  // Note: Total_Futbol_Academy_logo.jpg shows "California FC Barcelona Soccer Foundation"
  // which appears to be affiliated with Total Futbol Academy
  'california fc barcelona': 'Total_Futbol_Academy_logo.jpg',
};

/**
 * Load the club logo lookup JSON file
 */
async function loadLogoLookup() {
  if (logoLookupCache) return logoLookupCache;

  if (loadingPromise) return loadingPromise;

  loadingPromise = fetch('/club_logo_lookup.json')
    .then(res => res.json())
    .then(data => {
      // Merge with additional mappings
      logoLookupCache = { ...data, ...ADDITIONAL_MAPPINGS };
      return logoLookupCache;
    })
    .catch(err => {
      console.warn('Failed to load club logos:', err);
      logoLookupCache = { ...ADDITIONAL_MAPPINGS };
      return logoLookupCache;
    });

  return loadingPromise;
}

/**
 * Normalize club name for logo lookup
 */
function normalizeClubName(name) {
  if (!name) return '';
  return name.toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Find the best matching logo for a club name
 */
function findLogoForClub(clubName, lookup) {
  if (!clubName || !lookup) return null;

  const normalized = normalizeClubName(clubName);

  // Direct match - exact
  if (lookup[normalized]) {
    return lookup[normalized];
  }

  const sortedKeys = Object.keys(lookup).sort((a, b) => b.length - a.length);

  // Try word-boundary-aware partial matches
  // Only match if the key appears as a complete word sequence in the club name
  for (const key of sortedKeys) {
    // Skip very short keys to avoid false positives
    if (key.length < 6) continue;

    // Check if key is at word boundary in normalized name
    const keyPattern = new RegExp(`(^|\\s)${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\s|$)`);
    if (keyPattern.test(normalized)) {
      return lookup[key];
    }

    // Check if normalized is at word boundary in key
    const namePattern = new RegExp(`(^|\\s)${normalized.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\s|$)`);
    if (namePattern.test(key)) {
      return lookup[key];
    }
  }

  // Try matching without common suffixes
  const cleanName = normalized
    .replace(/\s+(fc|sc|sa|soccer|club|academy|youth|futbol|soccer club)$/g, '')
    .trim();

  for (const key of sortedKeys) {
    const cleanKey = key
      .replace(/\s+(fc|sc|sa|soccer|club|academy|youth|futbol|soccer club)$/g, '')
      .trim();

    // Require exact match of cleaned names or significant overlap
    if (cleanName === cleanKey) {
      return lookup[key];
    }

    // Only allow contains match if the shorter string is at least 8 chars
    if (cleanKey.length >= 8 && cleanName.includes(cleanKey)) {
      return lookup[key];
    }
    if (cleanName.length >= 8 && cleanKey.includes(cleanName)) {
      return lookup[key];
    }
  }

  // Try matching first significant words (at least 2 words, minimum 10 chars)
  const words = normalized.split(' ');
  for (let i = Math.min(words.length, 4); i >= 2; i--) {
    const partial = words.slice(0, i).join(' ');
    if (partial.length < 8) continue;

    if (lookup[partial]) {
      return lookup[partial];
    }

    for (const key of sortedKeys) {
      if (key.length >= 8 && (key.startsWith(partial) || partial.startsWith(key))) {
        return lookup[key];
      }
    }
  }

  return null;
}

/**
 * Hook to get a club's logo
 * @param {string} clubName - The name of the club
 * @returns {{ logoUrl: string|null, isLoading: boolean }}
 */
export function useClubLogo(clubName) {
  const [logoUrl, setLogoUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function findLogo() {
      setIsLoading(true);
      const lookup = await loadLogoLookup();

      if (cancelled) return;

      const filename = findLogoForClub(clubName, lookup);
      if (filename) {
        setLogoUrl(`/club_logos/${filename}`);
      } else {
        setLogoUrl(null);
      }
      setIsLoading(false);
    }

    findLogo();

    return () => { cancelled = true; };
  }, [clubName]);

  return { logoUrl, isLoading };
}

/**
 * Get club logo URL synchronously if lookup is already loaded
 * Returns null if not found or not loaded yet
 */
export function getClubLogoSync(clubName) {
  if (!logoLookupCache) return null;
  const filename = findLogoForClub(clubName, logoLookupCache);
  return filename ? `/club_logos/${filename}` : null;
}

/**
 * Preload the logo lookup (call on app start)
 */
export async function preloadLogoLookup() {
  return loadLogoLookup();
}

export default useClubLogo;
