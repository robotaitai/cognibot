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
3) **Versioning**: Before writing new files, check for existing architecture files in `.cognibot/architecture/`.
   - If `architecture.json` exists, create a timestamp-based directory like `.cognibot/architecture/history/2023-10-27T10:00:00Z/` and move the existing `architecture.md`, `architecture.mmd`, and `architecture.json` into it. This preserves history.
4) Identify the main bringup/launch entrypoints and core packages.
5) Build a layered architecture:
   - mission / autonomy / teleop / safety / vehicle / perception (adjust to repo reality)
6) Produce Mermaid diagram:
   - clusters per layer
   - modules inside
   - edges labeled with topic/service names when known
7) Produce `architecture.json` following the schema, including:
   - layers, modules (packages, entrypoints)
   - edges + apis + evidence + confidence
   - unknowns list
8) Write all generated files to `.cognibot/architecture/`:
   - `architecture.mmd`, `architecture.json`, `architecture.md`

Finally:
- Summarize what changed vs the previous architecture (if one was archived).