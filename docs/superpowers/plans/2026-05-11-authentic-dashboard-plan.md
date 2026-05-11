# Implementation Plan: Authentic Dashboard

**Required Skills:** 
- `caveman` (Active globally for token optimization)
- `subagent-driven-development` (Fresh subagent per task)
- `test-driven-development` (No code without failing tests first)
- `using-superpowers` (Invoke applicable domain skills dynamically)
- `antigravity-design-expert` (For UI/UX task)

## Tasks

### Task 1: TDD State Logic for Real Telemetry
- **Description:** Write failing tests for measuring TTFB and updating loading phases based on SSE events (`ROUTER`, `TEXT`), replacing the fake interval timer.
- **Files:** `frontend/src/hooks/useChatStream.test.ts` (or similar state logic file).

### Task 2: Implement Real Telemetry Logic
- **Description:** Update state management to record `startTime` on submit, calculate TTFB on first `TEXT` chunk, and map `ROUTER` intent to loading status. Delete `STEP_SEQUENCES`.
- **Files:** `frontend/src/components/Dashboard.tsx`

### Task 3: Antigravity UI & Clean Header
- **Description:** Remove fake strings (`LATENCY: 12MS`, `V1.0.4`, etc). Apply `backdrop-filter: blur`, smooth Framer Motion transitions for chat bubbles and loading indicators. Display real TTFB and environment.
- **Files:** `frontend/src/components/Dashboard.tsx`

### Task 4: Integration Verification
- **Description:** Run full frontend tests. Verify SSE chunks correctly transition UI from Phase 1 -> Phase 2 -> Phase 3 without fake delays.
- **Files:** E2E/Integration tests.
