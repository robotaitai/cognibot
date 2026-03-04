# cognibot
**Traceable agent memory + repo brain for robotics and ROS 2.**  
A Cursor plugin + CLI that turns “agent work” into a reproducible, inspectable, low-token workflow.

cognibot generates:
- an **agent-first markdown brain** (small, structured context)
- a **human-friendly HTML dashboard** you can open locally
- a **trace ledger** of agent runs, changes, commands, and artifacts

So you always know:
- what the agent “knows”
- what it changed
- why it changed it
- what evidence it produced

> cognibot does not include an LLM. It makes LLM-based agents (Cursor, Claude Code, etc.) cheaper, clearer, and safer to operate.

---

## why cognibot exists

### clarity
Robotics repos grow fast, and the real truth is scattered across:
- `package.xml` and deps
- launch files
- params yaml
- config stacks
- interface definitions (msg/srv/action)
- scripts, docs, and tribal knowledge

Agents and humans both pay the tax:
- long onboarding
- repeated repo scanning
- “where is this configured?” dead ends
- accidental edits in the wrong place

**cognibot generates a canonical brain** that summarizes the repo structure and key entry points in a format agents can use immediately and humans can verify.

### traceability
Agent-driven changes are often “chatty” but not auditable.
In robotics, that’s dangerous, because regressions are rarely code-only.

cognibot logs every run as a ledger tied to:
- git commit (and dirty state)
- files read / modified
- commands executed + exit codes
- produced artifacts (logs, metrics, reports)
- references to the brain snapshot used

So debugging becomes: “show me the run, show me the evidence”, not “try to remember what happened in chat”.

### cost effectiveness (token + time)
Agents are expensive when they repeatedly re-read your repo and “reconstruct context” from scratch.

cognibot reduces cost by giving agents a small, stable, structured context:
- the agent reads `brain.md` (and a few JSON files) instead of crawling hundreds/thousands of files
- you can measure the delta (bytes/words/token proxy)
- you can enforce that agent work is grounded in recorded sources

This typically reduces:
- context size
- repeated scans
- wrong fixes caused by missing config context
- time-to-diagnose regressions

---

## what you get

### 1) agent brain (markdown)
A generated, concise file designed to be dropped into agent context:
- repo identity (commit, dirty, timestamp)
- packages overview (build type, deps)
- launch entry points
- config/params inventory
- interfaces inventory
- pointers to “where the real behavior is defined”

### 2) human brain (static HTML)
Open locally, no server required:
- browse packages / launch files / interfaces
- see provenance header
- later: browse run history, diffs, evidence artifacts

### 3) run ledger
A structured log of “what happened”:
- intent → plan → actions → evidence → outcome
- what files were touched
- what commands were run
- what changed since last run

> We don’t expose hidden chain-of-thought. We expose **engineering trace** that’s actually useful and auditable.

---

## how it helps Cursor/Claude agents work better

When an agent has access to cognibot:
- it stops “guessing” the repo structure, it reads a **canonical snapshot**
- it can query deterministic tools instead of asking you to run commands
- it writes changes with an audit trail (run ledger)
- it produces evidence artifacts (reports, logs, metrics) as part of the workflow

Net effect:
- fewer tokens wasted on repo-reading
- fewer wrong edits
- faster debug loops
- reliable collaboration between humans and agents

---

## quickstart

### install (dev)
```bash
git clone <this-repo>
cd cognibot
python -m venv .venv
source .venv/bin/activate
pip install -e .