# GameGather MVP Backlog

This file captures the recommended first implementation plan for the project described in design.md.

## Product Goal

Build a small app that lets an organizer create a game proposal, let players register interest, reach a minimum threshold, start gathering, and collect attendance responses.

## Core Concept

Interest is not the same as commitment.

A player can show interest in a game, but the organizer should only begin a gather phase once enough interest has been collected.

## MVP Scope

### In Scope
- Create a game proposal
- View public game page
- Register interest
- Leave a game
- See live player count
- Start gathering
- Record attendance responses
- Send basic notifications
- Keep notifications separate from game logic

### Out of Scope for v1
- Role assignment
- Script management
- Recurring schedules
- Social features
- Full provider coverage beyond a first provider
- Convention/event management

---

## Recommended Build Order

### Phase 1: Core Domain and Data Model
- Create database schema
- Add organizer table
- Add player table
- Add game table
- Add registration table
- Add attendance response table
- Add notification queue table
- Define game states:
  - draft
  - open
  - minimum_reached
  - gathering
  - started
  - closed

### Phase 2: Organizer Workflow
- Add create game endpoint
- Add edit game endpoint
- View a single game
- View active players for a game
- Start a game gathering
- Close or finalize a game

### Phase 3: Player Workflow
- Create player record
- Register for a game
- Leave a game
- View current player count
- Respond to gathering request

### Phase 4: Notifications
- Emit events when important milestones happen
- Queue notifications for active players
- Keep provider logic separate from game logic
- Start with one provider such as email or Discord

### Phase 5: Deployment and Hardening
- Containerize the app
- Use SQLite in a Docker volume
- Add Traefik reverse proxy
- Add TLS and HTTPS
- Add health check route
- Add simple backup strategy
- [ ] Require authorization for `DELETE /registrations/{registration_id}`. It currently accepts a numeric registration ID without a private token or ownership check. Require a private registration token or an organizer token authorized for that registration's game, while preserving the open-game-only removal restriction. Add regression tests rejecting missing/invalid credentials and attempts to delete another registration or another organizer's game registration, and covering authorized removal and rejection after gathering starts.

---

## Suggested User Stories

### Organizer
1. As an organizer, I want to create a game proposal so that I can list the event.
2. As an organizer, I want to set minimum, ideal, and maximum player counts so that I can know when a game is viable.
3. As an organizer, I want to see the list of interested players so that I can manage the event.
4. As an organizer, I want to start gathering so that I can prompt players for attendance.
5. As an organizer, I want to see who is coming so that I can decide if the game can begin.

### Player
1. As a player, I want to join a game so that I can show interest.
2. As a player, I want to leave a game so that I can update my availability.
3. As a player, I want to see current counts so that I know how close the game is to being viable.
4. As a player, I want to respond to gathering requests so that the organizer knows if I can attend.

---

## Technical Recommendation

### Database
- SQLite for the MVP
- PostgreSQL later if needed

### Deployment
- Docker Compose
- Single app container
- SQLite volume for persistence
- Traefik as reverse proxy
- HTTPS via Let’s Encrypt

### App Architecture
- FastAPI for the API layer
- SQLite for persistence
- service layer for domain logic
- notification queue separated from direct sending logic

---

## Suggested First Milestone

The first milestone should be:

- create game
- add player registration
- count active players
- mark a game as gathering
- record attendance responses
- expose a summary route for the organizer

This is the smallest meaningful version of the product and aligns directly with the design concept.

---

## Suggested Next Task List

1. Set up database schema
2. Create organizer and player records
3. Create game record and public URL
4. Add join/leave registration logic
5. Add active-player counting
6. Add game state transitions
7. Add gather event and notifications
8. Add attendance response handling
9. Add organizer summary endpoint
10. Containerize app and deploy with SQLite volume

---

## Notes for Class Work

This file is intentionally written as a practical project backlog so it is easy to convert into:
- assignment tasks
- user stories
- implementation milestones
- testing goals
- progress checkpoints
