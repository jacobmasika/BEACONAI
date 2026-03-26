# BeaconAI Demo Script (3-5 Minutes)

Use this script to maximize judging score per minute.

## Target Length

- Primary cut: 4 minutes 20 seconds
- Backup cut: 3 minutes 30 seconds

## Demo Goal

Show one complete, believable workflow that proves:

- AI depth
- Offline readiness
- Technical quality
- Responsible AI judgment

## Recording Setup

- Start with browser app loaded and backend running.
- Keep one prepared missing-person sample and one sighting sample image.
- Keep network toggle ready (or simulate by disconnecting Wi-Fi).
- Zoom browser to readable text size.

## Time-Coded Script

### 0:00-0:20 | Hook

Narration:
"BeaconAI helps communities report and match missing-person sightings even in low-connectivity environments. We run image feature extraction on-device, queue reports offline, and sync for AI-assisted matching when online."

On screen:
- Show hero section and status pills.
- Briefly point to AI Search, Sighting, and Public Case panels.

### 0:20-1:05 | Public Case Intake

Narration:
"First, a family member can submit a structured missing-person report through the public portal. This standardizes critical details for responders."

On screen:
- Fill and submit the missing person form.
- Show successful submission state.
- Refresh and show case appears in recent list.

Judging signal:
- Real-world value
- UX and implementation quality

### 1:05-1:55 | Offline Sighting Capture

Narration:
"Now I simulate poor connectivity. A field responder captures a sighting photo and description. BeaconAI computes the embedding locally and stores the report safely until connectivity returns."

On screen:
- Turn network off.
- Upload sighting photo.
- Click Prepare Photo.
- Submit sighting and show queued/offline handling.

Judging signal:
- Offline-ready architecture
- Reliability under constraints

### 1:55-2:40 | Sync On Reconnect

Narration:
"When connectivity returns, queued sightings synchronize automatically, preserving continuity for field teams."

On screen:
- Turn network on.
- Trigger refresh/sync flow.
- Show sighting now appears in matches/recent data.

Judging signal:
- Technical robustness
- End-to-end data flow

### 2:40-3:35 | AI Search and Match Interpretation

Narration:
"BeaconAI supports AI-enhanced search with text, photo features, or both. Similarity is treated as triage support, not final identity proof."

On screen:
- Run AI search using text and optional image.
- Show returned results with confidence labels.
- Highlight score interpretation and caution.

Judging signal:
- Depth of AI integration
- Responsible AI framing

### 3:35-4:05 | Architecture Snapshot

Narration:
"Architecture is intentionally hybrid: on-device embedding in the frontend, vector search in backend, and resilient fallback paths. This balances privacy, speed, and operational reliability."

On screen:
- Quick architecture slide or README diagram section.
- Mention pgvector path and SQLite fallback.

Judging signal:
- Innovation and technical clarity

### 4:05-4:20 | Close

Narration:
"BeaconAI demonstrates practical AI for high-stakes response workflows: resilient, privacy-aware, and deployable with current tools."

On screen:
- Final app view.
- Show repo URL and contact/submission links.

## Optional 30-Second Cutdown (if needed)

Use only:
- Hook
- Offline capture and sync
- AI search result
- Responsible AI disclaimer

## Responsible AI One-Liners (Use Verbatim)

- "This system provides decision support, not identity verification."
- "Similarity scores are signals that require human review."
- "We minimize retained sensitive data by storing embeddings, not raw images, on backend workflows."

## Common Demo Failure Risks

- Spending too long on setup screens.
- Not actually showing offline to online transition.
- Claiming autonomous decision-making.
- Showing raw scores without interpretation.
- Ending without clear impact statement.

## Final Pre-Record Checklist

- [ ] Backend running and healthy.
- [ ] Frontend loaded with clean state.
- [ ] Sample data ready.
- [ ] Network toggle tested.
- [ ] One full dry run under 5 minutes.
- [ ] One backup recording captured.
