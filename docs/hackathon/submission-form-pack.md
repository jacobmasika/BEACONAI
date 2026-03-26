# BeaconAI Submission Form Pack

Use this file to copy and paste into the hackathon submission form quickly.

## 1) Project Name

BeaconAI

## 2) One-Line Pitch

BeaconAI is an offline-first missing-person support system that performs on-device image embedding, resilient offline queueing, and AI-assisted vector matching when connectivity returns.

## 3) Problem Statement

Missing-person response often breaks down in low-connectivity environments, where delayed reporting and fragmented information reduce the speed and quality of triage.

## 4) What We Built

BeaconAI includes:

- On-device image feature extraction in the browser.
- Offline sighting capture with IndexedDB queueing.
- Automatic sync when network connectivity is restored.
- Flask API for sightings, public case intake, and AI-enhanced search.
- Vector similarity matching with PostgreSQL + pgvector.
- SQLite fallback path for degraded or constrained environments.

## 5) AI Integration (Rubric Focus)

- Local inference in frontend for privacy-aware feature extraction.
- Embedding-based retrieval and matching in backend search pipelines.
- Hybrid text + image/embedding search path for missing-person discovery.
- Threshold-based match interpretation with human review expectation.

## 6) Responsible AI Practices

- Backend stores embeddings and case metadata, not raw facial photos.
- Similarity output is treated as decision support, not identity proof.
- Human-in-the-loop review is required before real-world action.
- Limitations and uncertainty are explicitly documented in project materials.

## 7) Innovation Highlights

- Practical offline-first architecture for high-stakes response workflows.
- Combined local inference and resilient cloud/server matching path.
- Structured case intake plus AI search in one integrated experience.

## 8) Real-World Impact

BeaconAI improves continuity of reporting and triage in unreliable network conditions, helping families, communities, and responders maintain actionable case flow.

## 9) Award Category Selection (Choose One)

Recommended primary category for current build:

- Offline-Ready AI Award

Alternative (if you center architecture narrative more strongly):

- Agentic System Architecture Award

## 10) Technical Links

Replace placeholders before submission:

- Repository URL: <PASTE_GITHUB_REPO_URL>
- Demo video URL (3-5 min): <PASTE_VIDEO_URL>
- Blog / technical write-up URL: <PASTE_BLOG_URL>
- Optional live deployment URL: <PASTE_DEPLOY_URL>

## 11) Team Metadata

- Team name: <TEAM_NAME>
- Team size: <1_TO_4>
- GitHub usernames: <USER1>, <USER2>, <USER3>, <USER4>

## 12) Suggested 120-Word Description

BeaconAI is an offline-first AI system for missing-person reporting and triage. It runs image feature extraction locally in the browser, queues reports when connectivity is unavailable, and syncs automatically once online. The backend uses vector similarity search to surface possible matches across missing-person records and public case reports. This architecture is designed for real-world constraints where stable internet cannot be assumed. BeaconAI prioritizes Responsible AI by treating similarity as decision support, requiring human review, and minimizing sensitive data retention through embedding-based workflows. The result is a resilient, practical tool that helps families, community reporters, and responders maintain continuity in time-critical search-and-rescue operations.

## 13) Final Pre-Submit Checks

- [ ] All links are public and working.
- [ ] Video duration is between 3 and 5 minutes.
- [ ] Category selection is aligned across form, blog, and demo.
- [ ] Team usernames are complete and accurate.
- [ ] No placeholder text remains.
