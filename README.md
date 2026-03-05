# cognibot
**Traceable agent memory + repo brain for robotics and ROS 2.**  
A Cursor plugin + CLI that turns "agent work" into a reproducible, inspectable, low-token workflow.

> cognibot does not include an LLM. It makes LLM-based agents (Cursor, Claude Code, etc.) cheaper, clearer, and safer to operate.

---

## what cognibot generates

### 1) brain.md — structured context for agents
A concise, auto-generated snapshot of your repo. Not a flat file listing — actual intelligence:

- **Your packages first** — separated from vendor dependencies, with:
  - topic wiring (what each node publishes/subscribes, with message types and node classes)
  - service wiring (servers and clients)
  - internal vs ROS dependency breakdown
- **Topic wiring table** — cross-package pub/sub connections at a glance
- **Service wiring table** — which package serves what, who calls it
- **Your launch files and params only** — vendor noise collapsed to a single summary line per vendor repo
- **Diff section** — what changed since the last scan (new packages, new topics, removed wiring)
- **Vendor packages** — grouped by repo, listed for reference only

### 2) knowledge.md — persistent AI memory
A file the AI reads at session start and writes to during work. Sections:

- **conventions** — coding patterns, naming rules, repo-specific practices
- **architecture notes** — how subsystems connect, design rationale
- **gotchas** — surprising behavior, non-obvious constraints
- **debug notes** — what broke, root cause, fix applied, what to watch for

This is how the agent gets smarter over time. Each session's learnings persist for the next one.

### 3) HTML dashboard
`cognibot ui` opens a local browser dashboard to browse packages, launch files, params, interfaces, and scan history.

### 4) run ledger
Structured log of agent runs: intent → actions → evidence → outcome.

---

## quickstart

### install
```bash
# one-liner: isolated venv, no project contamination
bash ~/.cursor/plugins/local/cognibot/scripts/cognibot.sh --help

# or manual:
python3 -m venv ~/.cognibot/venv
~/.cognibot/venv/bin/pip install -e ~/.cursor/plugins/local/cognibot
ln -sf ~/.cognibot/venv/bin/cognibot ~/.local/bin/cognibot
```

### scan a ROS2 workspace
```bash
cd ~/your_ros2_workspace
cognibot scan
```

This creates `.cognibot/` with:
```
.cognibot/
├── index.json                    # snapshot history
├── knowledge.md                  # persistent AI memory (created on first scan)
├── snapshots/
│   └── <snapshot_id>/
│       ├── brain.md              # the agent-readable brain
│       └── snapshot.json         # raw structured data
└── ui/
    └── index.html                # dashboard
```

### view the dashboard
```bash
cognibot ui          # scan + render + serve at http://localhost:8765
cognibot ui --host 0.0.0.0   # LAN access (e.g. from your laptop to Jetson)
```

### other commands
```bash
cognibot scan        # re-scan the repo, generate new brain.md
cognibot render      # regenerate the dashboard HTML
cognibot serve       # serve an existing .cognibot without re-scanning
cognibot stats       # print snapshot stats
cognibot doctor      # health checks
cognibot arch snapshot  # archive architecture artifacts into history
cognibot run start "fixing nav stack"   # start a tracked run
cognibot run log --run <id> --note "found the bug in tf listener"
cognibot run end --run <id> --status success
```

---

## how the agent uses cognibot

The Cursor rule `cognibot-brain-first.mdc` tells agents to:

1. **Read brain.md** before exploring the repo — it already has the package map, topic wiring, launch files, and params
2. **Read knowledge.md** for accumulated learnings from past sessions
3. **Write to knowledge.md** when discovering something non-obvious (gotchas, architecture decisions, debug findings)
4. **Re-scan** when packages, launch files, or topic wiring change

This is controlled by the rule file at:
```
~/.cursor/plugins/local/cognibot/rules/cognibot-brain-first.mdc
```

The rule is automatically picked up by Cursor when the workspace has a `.cognibot/` directory.

---

## how vendor vs user packages are detected

cognibot uses directory depth under `src/`:
- `src/<package_name>/` (depth 1) → **your package**
- `src/<vendor_repo>/<package_name>/` (depth 2+) → **vendor package**

This matches the standard ROS2 workspace convention where vendor repos are cloned as subdirectories (e.g., `src/depthai-ros/depthai_bridge/`).

Topic/service extraction only runs on your packages (not vendor code), keeping scans fast.

---

## how topic/service extraction works

cognibot parses Python and C++ source files for standard ROS2 API patterns:

**Python:**
- `self.create_publisher(MsgType, '/topic', ...)`
- `self.create_subscription(MsgType, '/topic', ...)`
- `self.create_service(SrvType, '/service', ...)`
- `self.create_client(SrvType, '/service', ...)`
- Node class detection via `class MyNode(Node):`

**C++:**
- `create_publisher<MsgType>("/topic", ...)`
- `create_subscription<MsgType>("/topic", ...)`
- `create_service<SrvType>("/service", ...)`
- `create_client<SrvType>("/service", ...)`

Results are deduplicated per package and shown in the brain's wiring tables.

---

## architecture generation

cognibot includes a prompt template for AI-driven architecture generation. When you ask the agent to "generate the architecture", it follows `cognibot-generate-architecture.md` to produce:

- `architecture.mmd` — Mermaid block diagram with layers and topic/service edges
- `architecture.json` — structured model with evidence and confidence scores
- `architecture.md` — human-readable explanation with unknowns

Use `cognibot arch snapshot` to version these artifacts before regenerating.
