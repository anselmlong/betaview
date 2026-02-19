# Draft: Video Playback Fix + Live Annotation Feature

## Requirements (confirmed)
- **Bug**: Video playback doesn't work - user has to download to view
- **Feature**: Live annotation while watching video
  - Body tension indicators
  - Foot stability markers
  - Elbow angle visualization

## Technical Findings

### Current Implementation
- **Frontend**: Next.js 14, React, TailwindCSS
- **Backend**: FastAPI + MediaPipe + OpenCV
- **Video serving**: `FileResponse` from `/video/{job_id}` endpoint
- **Video player**: Basic `<video src={url} controls />` in AnalysisResults.tsx

### Bug Root Cause Analysis (CONFIRMED)
**Primary cause**: Backend `/video/{job_id}` endpoint doesn't support HTTP Range requests.

HTML5 video players require Range requests for:
- Seeking (jumping to specific timestamp)
- Buffered playback
- Duration detection
- Progressive streaming

**Missing headers:**
- `Accept-Ranges: bytes` (tells browser streaming is supported)
- Proper handling of `Range` request header for 206 Partial Content responses
- `Content-Length` explicit header

**Frontend issues:**
- No `preload="metadata"` attribute
- No `crossOrigin` attribute for CORS
- No `onError` handler to diagnose failures

**Fix approach**: Replace `FileResponse` with custom streaming response that handles Range headers.

### Existing Assets for Annotation Feature
- MediaPipe pose data already extracted per frame
- Pose keypoints include: shoulders, hips, elbows, wrists, knees, ankles
- Metrics already calculated: body tension, foot stability, path efficiency
- `visualizer.py` already has skeleton overlay, hip trails, metrics display
- `VisualizationConfig` dataclass for configurable overlays
- `ClimbMetrics` dataclass with 15+ computed metrics

### Architecture Notes
- **Frontend**: Next.js 14, React hooks (no Redux/Zustand), TailwindCSS
- **Backend**: FastAPI, OpenCV, MediaPipe
- **State**: Simple useState in page.tsx, props drilling
- **Database**: None - in-memory jobs dict, file storage
- **Video flow**: Upload → process → annotate server-side → serve

### Annotation Architecture Options
1. **Server-side rendering** - User draws in browser, POST to backend, re-render video
2. **Client-side overlay** - Canvas over video, real-time preview, annotations stay as JSON
3. **Hybrid** - Canvas preview + backend re-render for export

## Open Questions
- [See interview below]

## Decisions Made
1. **Annotation type**: Visualize EXISTING computed metrics (not manual drawing)
2. **Timing**: Real-time during playback (annotations sync with video timestamp)
3. **Toggle control**: YES - users can toggle each overlay on/off independently
4. **Implementation**: Client-side Canvas rendering over video (required for toggles)
5. **Visualizations to build**:
   - Body tension heatmap (torso color zones: green=engaged, red=sagging)
   - Foot stability indicators (circles/pulses showing micro-adjustments)
   - Elbow angle arcs (showing extension angle for lock-off technique)
   - Hip path efficiency (enhanced trail with efficiency scoring)
6. **Skeleton handling**: Move to client-side (remove from baked video, make toggleable)
7. **Toggle UI**: Floating panel over video (corner overlay with switches)
8. **Testing**: Yes - set up vitest for frontend, add tests for new code
9. **Out of scope**: Manual drawing tools, mobile optimization

## Scope Boundaries

### IN SCOPE
- Fix video playback (HTTP Range header support)
- New API endpoint to serve per-frame pose data + metrics
- Remove skeleton baking from backend video processing
- Client-side Canvas overlay component synced with video
- 5 overlay types: Skeleton, Body tension, Foot stability, Elbow angles, Hip path
- Floating toggle panel UI
- Test infrastructure setup (vitest) + tests for new components

### OUT OF SCOPE (Explicit guardrails)
- Manual drawing/annotation tools
- Mobile optimization
- New metrics computation (use existing only)
- Database setup (keep in-memory storage)

## Visual Specs (from Metis review + user input)
- **Body tension**: Colored torso line (shoulder-to-hip) - green=engaged, yellow=slight sag, red=sagging
- **Foot stability**: Colored ankle circles - green=stable, pulse red when detecting micro-adjustments
- **Elbow angles**: Arc overlay showing extension angle
- **Hip path**: Windowed trail (last 90 frames, matching existing server-side behavior)
- **Skeleton**: Lines connecting keypoints (same as current server-side rendering)

## Video Output Strategy
- Generate BOTH: annotated video (for download) + clean video (for in-page viewing with client overlays)
- This preserves backward compatibility and gives users both options

## Technical Corrections from Metis
1. **Root cause**: Primary issue is `filename=` in FileResponse (sets Content-Disposition: attachment), not just missing Range support. Fix in two steps.
2. **Per-frame data**: ClimbMetrics only has aggregates. Frontend must compute per-frame values from raw keypoints.
3. **Pose data persistence**: Currently lost after processing. Must save to `{job_id}_poses.json`.
4. **Payload size**: 5-10MB for long videos. Use gzip compression.

## Testing Scope (bounded)
- 4 test files max: vitest config, drawing functions, toggle panel, pose data hook

## Scope Boundaries
- INCLUDE: [TBD]
- EXCLUDE: [TBD]
