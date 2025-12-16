# Youth Soccer Team Ranking App

## Project Overview
A web application (with future mobile version) that scrapes youth soccer club data from the internet to build a comprehensive database of teams, games, and players. The app ranks teams by various criteria and allows users to rate players and manage rosters.

## Core Goals
- Automatically collect and organize youth soccer data from multiple sources
- Provide accurate team rankings across multiple dimensions
- Create a community-driven platform for player ratings and roster management
- Scale from web to mobile platforms

## Data Model

### Teams
- Team name
- Club/organization
- Gender (boys/girls/co-ed)
- Age group
- Location (city, state, region)
- League/division
- Current ranking
- Season/year

### Games
- Home team
- Away team
- Date and time
- Score (if completed)
- Game type (league, tournament, friendly)
- Location/venue
- Status (scheduled, completed, cancelled)

### Players
- Name
- Team roster associations
- Position (if applicable)
- Jersey number
- Age/birth year
- User ratings (aggregate)

### Users
- Account info
- Teams they follow
- Players they've rated
- Contribution history

## Key Features

### 1. Data Scraping
- Scrape youth soccer websites for:
  - Team rosters
  - Game schedules
  - Past game scores
  - Tournament results
- Handle multiple data sources and formats
- Update data regularly (daily/weekly)

### 2. Team Rankings
- Rank teams by:
  - Gender
  - Age group
  - Location (regional, state, national)
  - League/division
- Ranking algorithm considers:
  - Win/loss record
  - Strength of schedule
  - Recent performance
  - Tournament results

### 3. Player Management
- Display team rosters
- User-submitted player ratings
- Add/edit player information
- Link players to multiple teams (if they move/play on multiple teams)

### 4. User Features
- Search teams by various filters
- View upcoming games
- View historical scores
- Rate and review players
- Follow specific teams
- Compare teams

## Tech Stack
**To be determined - add your choices here:**
- Frontend: 
- Backend: 
- Database: 
- Scraping tools: 
- Hosting: 

## Development Phases

### Phase 1: MVP (Current)
- [ ] Set up basic project structure
- [ ] Design database schema
- [ ] Build initial scraper for one data source
- [ ] Create basic team listing page
- [ ] Implement simple ranking algorithm

### Phase 2: Core Features
- [ ] Add multiple scraping sources
- [ ] Build team detail pages
- [ ] Implement game schedule display
- [ ] Create ranking system with filters
- [ ] Add user authentication

### Phase 3: User Interaction
- [ ] Player rating system
- [ ] Roster management
- [ ] User profiles
- [ ] Team following/favorites

### Phase 4: Mobile App
- [ ] Convert web app to mobile
- [ ] Optimize for mobile UX
- [ ] Add mobile-specific features

## Design Decisions

### Scraping Strategy
- **Frequency:** TBD (daily for schedules, weekly for historical data?)
- **Sources:** List specific websites here as we identify them
- **Data validation:** How to handle conflicting information from multiple sources

### Ranking Algorithm
- **Approach:** TBD (ELO-based? Point system? Hybrid?)
- **Update frequency:** After each game? Daily batch?
- **Historical weight:** How much to weight recent vs. older games

### Data Integrity
- How to prevent duplicate teams/players
- Handling team name changes
- Dealing with incomplete data
- User submission validation

## Current Status
**Last updated:** [Date]
**Current phase:** Planning/Initial Development
**Next steps:** 
1. Finalize tech stack
2. Set up development environment
3. Design database schema

## Notes & Ideas
- Consider adding team comparison feature
- Potential for predictive game outcomes
- Could add coaching resources section
- Think about data privacy for minors
- May need parent consent for player ratings

---

## For Claude (AI Assistant Instructions)
When working on this project:
- Always maintain consistent data structure
- Prioritize data accuracy and validation
- Keep scalability in mind (web → mobile)
- Focus on user-friendly interfaces (user is vibe coding, not a programmer)
- Suggest simple, maintainable solutions
- Explain technical decisions in plain language
