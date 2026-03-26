# BeaconAI: Offline-First AI for Missing Person Search and Rescue

Recommended category alignment for this draft: Offline-Ready AI Award

## TL;DR

BeaconAI is an offline-first missing-person support platform that performs local image embedding in the browser, queues reports when offline, and runs AI-assisted similarity matching in a Python backend once connectivity is available.

## 1) Problem

When a person goes missing, the first hours matter. In many field contexts, responders and families face low connectivity, fragmented reporting, and inconsistent handoff quality.

Existing tools often assume stable internet and centralized workflows. That fails in exactly the environments where rapid, resilient reporting is needed.

## 2) Why This Matters

- Families and community members need a way to submit structured missing-person reports quickly.
- Field responders need lightweight capture and deferred-sync workflows.
- Coordinators need consistent matching signals instead of purely manual triage.

BeaconAI targets this gap with an offline-first architecture and AI-assisted retrieval.

## 3) Solution Overview

BeaconAI provides three core capabilities:

1. On-device feature extraction from photos in the frontend.
2. Offline capture with local queueing until network returns.
3. Backend vector search and threshold-based possible-match identification.

It also includes a public case intake flow so families and community reporters can submit high-quality case data.

## 4) Architecture

### Frontend

- Uses Transformers.js to run image feature extraction locally.
- Stores pending sightings in IndexedDB when offline.
- Syncs pending reports when network is restored.

### Backend

- Flask API with routes for sightings, matches, public cases, and AI search.
- PostgreSQL + pgvector for scalable similarity search.
- SQLite fallback path for resilience in constrained environments.

### Data Flow

1. User captures image and description.
2. Frontend computes embedding locally.
3. If offline, payload is queued in IndexedDB.
4. When online, payload is submitted to API.
5. Backend compares embedding to active missing-person vectors.
6. If threshold is met, result is marked as possible match and a handoff payload is prepared.

## 5) AI Integration Details

- Model usage: local image feature extraction in browser.
- Retrieval strategy: vector similarity using cosine distance/similarity.
- Hybrid search: text and embedding-based search for missing-person records.
- Match policy: threshold-based interpretation for cautious triage.

This is assistive AI, not autonomous decision-making.

## 6) Responsible AI and Safety

BeaconAI follows a privacy-minimizing design:

- Raw facial photos are processed locally and not persisted by backend storage.
- Backend stores embeddings and case metadata needed for search workflows.
- Similarity scores are treated as signals, not proof of identity.
- Human review remains required before action.

Known limitations:

- Similarity quality depends on image quality, angle, and lighting.
- False positives and false negatives remain possible.
- Field outcomes depend on operational procedures beyond software.

## 7) Technical Implementation Notes

- API endpoints:
  - POST /api/sighting
  - GET /api/matches
  - POST /api/public/cases
  - GET /api/public/cases
  - POST /api/search/missing
- Deployment:
  - Vercel serverless API entrypoint plus static frontend routing.
- Reliability:
  - Client-side queue + backend fallback path for degraded conditions.

## 8) Demo Scenario Summary

In our demo, we show:

1. Submitting a missing-person report with context.
2. Capturing a new sighting while offline.
3. Automatic sync when online is restored.
4. AI-assisted search and possible-match output with confidence interpretation.

## 9) What We Built With AI During Development

- Used AI coding assistance to iterate endpoint contracts, validation, and error handling.
- Used AI assistance to speed up implementation of offline queue workflows.
- Used AI support to draft and refine architecture and Responsible AI documentation.

## 10) Results and Impact

BeaconAI improves operational readiness in constrained environments by combining:

- Offline-first user flows
- On-device AI inference
- Unified case intake and matching surfaces

The project demonstrates that practical, resilient AI systems can be built for high-stakes public-interest workflows.

## 11) Next Steps

- Add stronger evaluation metrics and threshold calibration tooling.
- Integrate external responder systems with audited handoff APIs.
- Expand multilingual support for broader community accessibility.
- Add explainability and confidence decomposition for better operator decisions.

## 12) Links

- Repository: <ADD_GITHUB_URL>
- Demo video: <ADD_VIDEO_URL>
- Technical write-up URL (this post): <ADD_BLOG_URL>
- Live app (optional): <ADD_DEPLOY_URL>

## 13) Submission Notes

- Keep your video and blog claims consistent with what is actually shown in the demo.
- If you choose Agentic System Architecture instead, update title and sections 5 and 11 accordingly.
- Include one architecture diagram screenshot in the published post.

## Suggested Submission Title Variants

- BeaconAI: Offline-First AI for Missing Person Search and Rescue
- BeaconAI: Resilient Missing-Person Workflows with On-Device AI
- BeaconAI: Low-Connectivity AI Matching for Community Search Response
