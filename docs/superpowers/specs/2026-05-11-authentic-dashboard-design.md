# Authentic Dashboard Design

## Context
Remove "vibe-coded" fake logs/latency in `Dashboard.tsx`. Replace with real SSE network events, TTFB measurement, and Antigravity glassmorphism UI.

## Architecture & Data Flow
- **Telemetry:** Measure Time To First Byte (TTFB) from `/chat/stream` fetch start to first `TEXT` chunk. Display as real latency.
- **Environment:** Fetch or detect environment (`NODE_ENV` or API URL) instead of fake `/dev/neural_hub_01`.
- **Loading State:** 
  - Phase 1: Glow/Pulse -> "Establishing connection..."
  - Phase 2: On `ROUTER` event -> "Route identified: [INTENT]. Awaiting token stream..."
  - Phase 3: On `TEXT` event -> Fade out loader, stream text.
- **Aesthetics:** `backdrop-filter: blur(12px)`, layered Z-index, staggered Framer Motion fade-ins. No fake text or hardcoded versions.

## Constraints
- TDD mandatory for new state logic.
- Subagent-driven development for execution.
- Caveman mode active to save tokens.
