# BeaconAI Hackathon Submission Checklist

Use this checklist as your single source of truth before final submission.

## 1) Mandatory Submission Requirements (Must-Have)

- [ ] Public GitHub repository URL is final and accessible.
- [ ] Technical blog post/write-up is published and linked.
- [ ] Public 3-5 minute demo video is uploaded and linked (YouTube/Vimeo/Facebook).
- [ ] GitHub usernames for all team members are listed in the submission form.
- [ ] Team size complies with rules (1 to 4 members).

## 2) Rubric-Mapped Execution Checklist

### Depth of AI Integration (25%)

- [ ] Frontend generates on-device embeddings (Transformers.js) and uses them in search/report flow.
- [ ] Backend performs vector similarity matching with clear thresholding logic.
- [ ] Hybrid search is demonstrated (text and image/embedding).
- [ ] At least one end-to-end AI workflow is shown live in demo.
- [ ] Prompting/AI-tool usage in build process is documented in blog.

Evidence pointers in code:
- frontend/app.js
- backend/app/routes.py
- backend/app/matcher.py
- backend/app/models.py

### Technical Implementation and UX (20%)

- [ ] Golden path works in one continuous demo run with no blockers.
- [ ] Form validation and error states are understandable.
- [ ] Search results are readable and confidence-tagged.
- [ ] Setup instructions are reproducible from README.
- [ ] Test suite passes locally before recording and before submission.

### Responsible AI Patterns (15%)

- [ ] Data minimization is explicit: raw images are not persisted server-side.
- [ ] User-facing limitations and false-positive risks are documented.
- [ ] Human-in-the-loop expectation is stated (assistive system, not autonomous authority).
- [ ] Similarity thresholds and uncertainty are explained in plain language.
- [ ] Safety/fallback behavior is shown (offline queue, cautious match interpretation).

### Solution Value (15%)

- [ ] Problem statement is concrete: missing-person response under poor connectivity.
- [ ] Beneficiaries are clearly named (families, field responders, public reporters).
- [ ] Practical impact is quantified or estimated (response speed, handoff quality, coverage).
- [ ] Constraints are realistic (low-connectivity, device limitations, triage urgency).

### Innovation and Creativity (10%)

- [ ] Distinct angle is clear (offline-first + local inference + vector matching + handoff payload).
- [ ] Category strategy is explicit (Offline-Ready AI or Agentic System Architecture).
- [ ] Architecture decisions and tradeoffs are presented (privacy, reliability, scale).

### Documentation and Storytelling (10%)

- [ ] Story arc follows Problem -> Why now -> Solution -> Architecture -> Demo -> Impact -> Limits -> Next steps.
- [ ] Blog includes architecture diagram (static image or Mermaid rendered screenshot).
- [ ] Demo narration uses a tight, no-fluff script.
- [ ] README links all final assets (video, blog, category choice).

### Award Category Compliance (5%)

- [ ] A single primary award category is selected.
- [ ] Submission narrative is aligned to that category from title to conclusion.
- [ ] Category-specific proof points appear in video and blog.

## 3) Category Positioning Decision

Choose one and commit:

- [ ] Offline-Ready AI Award
  - Required emphasis: resilient performance in low/no network settings.
  - BeaconAI proof points: IndexedDB queueing, deferred sync, SQLite fallback, local embedding.

- [ ] Agentic System Architecture Award
  - Required emphasis: orchestrated decision flow, reliability, and transparent handoff design.
  - BeaconAI proof points: match evaluation pipeline, notification hook, law-enforcement handoff schema.

Recommended default for current implementation: Offline-Ready AI.

## 4) 48-Hour Tactical Plan

### T-48 to T-24

- [ ] Lock category and update README intro accordingly.
- [ ] Publish technical blog.
- [ ] Dry-run demo three times and remove all dead time.
- [ ] Capture final screen recording in one clean take plus backup take.

### T-24 to T-0

- [ ] Re-run tests.
- [ ] Verify all links from README are public and correct.
- [ ] Verify repo includes setup, architecture, and Responsible AI section.
- [ ] Submit and save confirmation screenshot.

## 5) Final Quality Gate (Go/No-Go)

Ship only when all are true:

- [ ] Demo shows one complete offline-to-online scenario.
- [ ] Demo shows one complete AI search/match scenario.
- [ ] Blog explains what AI does and what it does not do.
- [ ] No broken links, no missing assets, no placeholder text.
- [ ] Submission form fields are fully complete.
