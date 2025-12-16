# Youth Soccer Leagues - Scraping Strategy Summary

## Platforms Discovered (6 Total)

### 1. GotSport (system.gotsport.com) - ~50% of leagues
- **Used by:** US Club Soccer NPL, some US Youth Soccer National League conferences, many state associations
- **URL Pattern:** `https://system.gotsport.com/org_event/events/{EVENT_ID}`
- **Scraping:** Requires Playwright (robots.txt blocked)
- **Your existing scrapers:** Girls Academy scraper should work as template

### 2. Squadi (registration.us.squadi.com) - ~25% of leagues (NEW!)
- **Used by:** US Youth Soccer National League (Team Premier, Club Premier 1&2, Winter Events)
- **URL Pattern:** Complex query string with organisationKey, competitionUniqueKey, yearId
- **Scraping:** Need to investigate - appears to be newer platform
- **Data format:** JSON API likely available

### 3. TotalGlobalSports (public.totalglobalsports.com) - ~10% of leagues
- **Used by:** ECNL, ECNL-RL, some Texas NPL leagues (STXCL, TCSL)
- **URL Pattern:** `https://public.totalglobalsports.com/public/event/{EVENT_ID}/schedules-standings`
- **Your existing scrapers:** ECNL scraper covers this

### 4. Affinity Soccer (*.affinitysoccer.com) - ~5% of leagues (NEW!)
- **Used by:** Georgia Soccer (gs.affinitysoccer.com)
- **URL Pattern:** Complex GUID-based URLs
- **Scraping:** Need to investigate structure

### 5. SincSports (soccer.sincsports.com) - ~5% of leagues
- **Used by:** Carolina Champions League, some tournament cups
- **URL Pattern:** `https://soccer.sincsports.com/TTContent.aspx?tid={TOURNAMENT_ID}`
- **Scraping:** Standard HTML scraping likely works

### 6. Custom Platforms - ~5% of leagues
- **Ohio Travel Soccer League:** ohtsl.com (fully custom)
- Each requires individual scraper development

---

## What's Still Missing

### State Associations to Explore (55 total)
Each state under US Youth Soccer has its own league structure. Priority states:

| State | Website | Priority | Notes |
|-------|---------|----------|-------|
| California North | calnorth.org | HIGH | Major soccer state |
| California South | calsouth.com | HIGH | Major soccer state |
| Texas (North) | ntxsoccer.org | HIGH | Has Frontier Conference |
| Texas (South) | stxsoccer.org | HIGH | Already have STXCL |
| Florida | fysa.com | HIGH | Major soccer state |
| New York (East) | enysoccer.com | HIGH | Major metro area |
| New Jersey | njyouthsoccer.com | HIGH | Major soccer state |
| Pennsylvania (East) | epysa.org | MEDIUM | |
| Pennsylvania (West) | pawest-soccer.org | MEDIUM | |
| Ohio | ohio-soccer.org | MEDIUM | Already have OHTSL separately |
| Illinois | illinoisyouthsoccer.org | MEDIUM | |
| Michigan | michiganyouthsoccer.org | MEDIUM | |
| Virginia | vysa.com | MEDIUM | Already have VPSL |
| Maryland | msysa.org | MEDIUM | |
| Massachusetts | mayouthsoccer.org | MEDIUM | |
| Washington | washingtonyouthsoccer.org | MEDIUM | Already have WPL |
| Colorado | coloradosoccer.org | MEDIUM | |
| ... and 38 more states | | LOW | |

### Other Missing Leagues
- **US Youth Soccer State Cups** - Each state runs State Cup and Presidents Cup
- **US Youth Soccer ODP leagues** - Olympic Development Program regional leagues
- **Regional tournament circuits** - Various regional showcase events

---

## Recommended Scraper Priority

### Phase 1: GotSport Master Scraper
- Covers ~50% of all leagues
- Template exists (GA scraper)
- **Leagues covered:** 25+ US Club Soccer NPL leagues, 8+ US Youth Soccer NL conferences

### Phase 2: Squadi Scraper (NEW PLATFORM)
- Covers ~25% of leagues (US Youth Soccer National League)
- Need to reverse-engineer API
- **Leagues covered:** 20+ Team Premier and Club Premier conferences

### Phase 3: State Association Scrapers
- Each state needs investigation
- Many use GotSport, some use Affinity, some custom
- Start with high-priority states (CA, TX, FL, NY, NJ)

### Phase 4: Custom Scrapers
- Ohio Travel Soccer League
- Any other custom platforms discovered

---

## Platform Detection Strategy

When exploring a new state/league, look for these patterns:

1. **GotSport:** URL contains `system.gotsport.com` or `gotsport`
2. **Squadi:** URL contains `squadi.com`
3. **TotalGlobalSports:** URL contains `totalglobalsports.com`
4. **Affinity Soccer:** URL contains `affinitysoccer.com`
5. **SincSports:** URL contains `sincsports.com`
6. **SportsEngine:** URL contains `sportsengine.com` or site is built on SportsEngine
7. **Custom:** Anything else - requires individual investigation

---

## Current Totals

| Category | Count |
|----------|-------|
| US Club Soccer NPL leagues | 25 |
| US Club Soccer sub-NPL leagues | 9 |
| US Youth Soccer National League | 26 |
| State Association leagues | 4 (need to expand) |
| Custom platform leagues | 2 |
| **Total Verified** | **66** |
| **Still Need to Explore** | 55 state associations |
