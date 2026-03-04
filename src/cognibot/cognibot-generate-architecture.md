---
name: cognibot-generate-architecture
description: Generate a layered block diagram + API map for this ROS2 repo (written by the agent).
---

You are the project architect.

Goal:
- Generate `.cognibot/architecture/architecture.mmd` (Mermaid block diagram)
- Generate `.cognibot/architecture/architecture.json` (structured model + evidence)
- Generate `.cognibot/architecture/architecture.md` (explanation + sources + unknowns)

Rules:
- Do NOT guess. Every edge/API must include evidence.
- If unsure, put it under `unknowns` and explain what to inspect next.

Steps:
1) Ensure snapshot exists:
   - Run: `cognibot scan --repo .`
2) Read the latest `.cognibot/snapshots/<id>/brain.md`.
3) Identify the main bringup/launch entrypoints and core packages.
4) Build a layered architecture:
   - mission / autonomy / teleop / safety / vehicle / perception (adjust to repo reality)
5) Produce Mermaid diagram:
   - clusters per layer
   - modules inside
   - edges labeled with topic/service names when known
6) Produce `architecture.json` following the schema, including:
   - layers, modules (packages, entrypoints)
   - edges + apis + evidence + confidence
   - unknowns list
7) Write all generated files to `.cognibot/architecture/`:
   - `architecture.mmd`, `architecture.json`, `architecture.md`

Finally:
- Summarize what changed vs the previous architecture (if one was archived).