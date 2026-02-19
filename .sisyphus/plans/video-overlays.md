# Video Playback Fix + Toggleable Metric Overlays

## TL;DR

> **Quick Summary**: Fix video playback bug (currently forces download) and add real-time toggleable metric overlays that visualize body tension, foot stability, elbow angles, hip path, and skeleton during video playback.
> 
> **Deliverables**:
> - Fixed video streaming endpoint with Range header support
> - New pose data API endpoint (`GET /job/{job_id}/pose-data`)
> - Client-side Canvas overlay component synced with video playback
> - 5 toggleable overlay types: skeleton, body tension, foot stability, elbow angles, hip path
> - Floating toggle panel UI
> - Test infrastructure (vitest) with tests for new components
> 
> **Estimated Effort**: Medium (5-7 days)
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 1 → Task 2 → Task 5 → Task 8 → Task 12 → Final Verification

---

## Context

### Original Request
User reported video playback doesn't work (must download to view) and requested live annotation capability for visualizing climbing technique metrics during video playback.

### Interview Summary
**Key Discussions**:
- **Annotation type**: Auto-visualize existing computed metrics (not manual drawing)
- **Timing**: Real-time during playback, synced with video timestamp
- **Toggle control**: Users can toggle each overlay type independently
- **Skeleton**: Move from server-side baking to client-side rendering (toggleable)
- **UI**: Floating toggle panel in corner of video
- **Testing**: Set up vitest with bounded scope (4 test files max)

**Research Findings**:
- **Root cause**: Primary issue is `filename=` parameter in FileResponse setting `Content-Disposition: attachment`. Secondary issue is missing Range header support for seeking/Safari.
- **Data availability**: Per-frame keypoints exist in `PoseFrame.keypoints`, but per-frame metrics don't. Frontend must compute from raw keypoints.
- **Pose data loss**: Currently `pose_frames` are lost after processing - need to persist to JSON file.
- **Codec concern**: Original uploads may be non-web-compatible formats; need to transcode "clean" video.

### Metis Review
**Identified Gaps** (addressed):
- Root cause misdiagnosis: Fixed - sequencing as two-step fix (filename removal → Range support)
- Per-frame metrics: Resolved - frontend computes from keypoints
- Visual specs undefined: Resolved via user input (colored torso line, ankle circles)
- Testing scope unbounded: Resolved - capped at 4 test files
- Pose data persistence: Added to plan

---

## Work Objectives

### Core Objective
Fix the video playback bug and add toggleable real-time metric overlays that help climbers analyze their technique during video review.

### Concrete Deliverables
- `backend/main.py`: Fixed `/video/{job_id}` endpoint with Range support + new `/job/{job_id}/pose-data` endpoint
- `frontend/components/VideoOverlay.tsx`: Canvas overlay component
- `frontend/components/TogglePanel.tsx`: Floating control panel
- `frontend/lib/overlays/`: Drawing functions for 5 overlay types
- `frontend/hooks/usePoseData.ts`: Hook for fetching and managing pose data
- `frontend/vitest.config.ts` + test files

### Definition of Done
- [ ] `curl -sI http://localhost:8000/video/{job_id}` returns 200 with `Accept-Ranges: bytes` and NO `attachment` in Content-Disposition
- [ ] `curl -sI -H "Range: bytes=0-1" http://localhost:8000/video/{job_id}` returns 206 with `Content-Range` header
- [ ] Video plays inline in browser without download prompt
- [ ] Video seeking works in Safari, Chrome, Firefox
- [ ] All 5 overlay types render correctly and can be toggled
- [ ] `cd frontend && npx vitest run` passes all tests
- [ ] `cd frontend && npm run build` succeeds with no errors

### Must Have
- Video plays inline without download prompt
- Range headers support for seeking
- Pose data endpoint returns per-frame keypoints with coordinates
- Canvas overlay synced with video currentTime (±100ms tolerance)
- All 5 overlay types: skeleton, body tension, foot stability, elbow angles, hip path
- Each overlay independently toggleable
- Both annotated (for download) and clean (for viewing) videos generated
- Vitest setup with tests for drawing functions

### Must NOT Have (Guardrails)
- NO manual drawing/annotation tools
- NO mobile-specific optimizations
- NO new backend metrics computations (use existing keypoint data)
- NO state management libraries (Zustand/Redux) - use useState/useRef only
- NO gradients, particle effects, or glow on overlays - solid lines/circles only
- NO more than 4 test files
- NO WebSocket/SSE for pose data - single fetch after job completion
- NO draggable/resizable toggle panel - static floating div
- NO changes to existing ClimbMetrics calculation logic

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO → will set up
- **Automated tests**: YES (tests-after)
- **Framework**: vitest (recommended for Vite/Next.js projects)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

| Deliverable Type | Verification Tool | Method |
|------------------|-------------------|--------|
| Backend endpoints | Bash (curl) | Send requests, assert status + headers + response |
| Frontend components | Playwright | Navigate, interact, assert DOM, screenshot |
| Drawing functions | Vitest | Unit tests with assertions |

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — bug fix + foundation):
├── Task 1: Fix FileResponse Content-Disposition header [quick]
├── Task 2: Add HTTP Range header support [quick]
├── Task 3: Persist pose data to JSON during processing [quick]
└── Task 4: Create pose-data API endpoint [quick]

Wave 2 (After Wave 1 — frontend foundation):
├── Task 5: Create VideoOverlay canvas component [deep]
├── Task 6: Create usePoseData hook [quick]
├── Task 7: Set up vitest infrastructure [quick]
└── Task 8: Generate clean video alongside annotated [quick]

Wave 3 (After Wave 2 — overlay implementations):
├── Task 9: Implement skeleton drawing function [quick]
├── Task 10: Implement body tension overlay [quick]
├── Task 11: Implement foot stability overlay [quick]
├── Task 12: Implement elbow angle overlay [quick]
└── Task 13: Implement hip path overlay [quick]

Wave 4 (After Wave 3 — UI + tests):
├── Task 14: Create TogglePanel component [visual-engineering]
├── Task 15: Integrate overlays into AnalysisResults [quick]
├── Task 16: Write drawing function tests [quick]
└── Task 17: Write component integration tests [quick]

Wave FINAL (After ALL tasks — verification):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real QA - Playwright (unspecified-high)
└── F4: Scope fidelity check (deep)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|------------|--------|------|
| 1 | — | 2 | 1 |
| 2 | 1 | 5, 15 | 1 |
| 3 | — | 4 | 1 |
| 4 | 3 | 6 | 1 |
| 5 | 2 | 9-13, 15 | 2 |
| 6 | 4 | 5, 15 | 2 |
| 7 | — | 16, 17 | 2 |
| 8 | — | 15 | 2 |
| 9-13 | 5 | 14, 15 | 3 |
| 14 | 9-13 | 15 | 4 |
| 15 | 2, 5, 6, 8, 9-13, 14 | F1-F4 | 4 |
| 16 | 7, 9-13 | F1-F4 | 4 |
| 17 | 7, 14, 15 | F1-F4 | 4 |

### Agent Dispatch Summary

| Wave | # Parallel | Tasks → Agent Category |
|------|------------|----------------------|
| 1 | **4** | T1-T4 → `quick` |
| 2 | **4** | T5 → `deep`, T6-T8 → `quick` |
| 3 | **5** | T9-T13 → `quick` |
| 4 | **4** | T14 → `visual-engineering`, T15-T17 → `quick` |
| FINAL | **4** | F1 → `oracle`, F2-F3 → `unspecified-high`, F4 → `deep` |

---

## TODOs

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `cd frontend && npm run build` + `npx vitest run`. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA - Playwright** — `unspecified-high` (+ `playwright` skill)
  Start from clean state. Execute EVERY QA scenario from EVERY task. Test video playback in browser. Test all 5 overlay toggles. Test seeking behavior. Save screenshots to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | VERDICT`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 2 | `fix(backend): enable video streaming with Range headers` | main.py | curl tests |
| 4 | `feat(backend): add pose-data endpoint` | main.py | curl tests |
| 8 | `feat(backend): generate clean video for client overlays` | main.py, visualizer.py | file exists |
| 7 | `chore(frontend): set up vitest` | vitest.config.ts, package.json | npx vitest run |
| 13 | `feat(frontend): implement overlay drawing functions` | lib/overlays/*.ts | vitest |
| 15 | `feat(frontend): integrate video overlays with toggle panel` | components/*.tsx | build + manual |
| 17 | `test(frontend): add overlay component tests` | *.test.ts | vitest |

---

## Success Criteria

### Verification Commands
```bash
# Video streams inline (not downloaded)
curl -sI http://localhost:8000/video/{job_id} | grep -i content-disposition
# Expected: empty OR "inline" (NOT "attachment")

# Range requests work
curl -sI -H "Range: bytes=0-1" http://localhost:8000/video/{job_id}
# Expected: HTTP 206, Content-Range header present

# Pose data endpoint
curl -s http://localhost:8000/job/{job_id}/pose-data | python3 -c "import json,sys; d=json.load(sys.stdin); print('frames:', len(d['frames']))"
# Expected: frames: <number>

# Frontend builds
cd frontend && npm run build
# Expected: exit 0

# Tests pass
cd frontend && npx vitest run
# Expected: exit 0, all tests pass
```

### Final Checklist
- [ ] Video plays inline without download prompt (Chrome, Firefox, Safari)
- [ ] Video seeking works
- [ ] All 5 overlays render and toggle correctly
- [ ] Pose data endpoint returns valid data
- [ ] Both annotated and clean videos generated
- [ ] All tests pass
- [ ] Build succeeds
