---
name: cognibot-ui
description: Start the Brain Studio UI server (accessible via LAN).
---

Goal: Start the cognibot UI server so the user can view the brain/architecture from another device.

Steps:
1. Run: `cognibot ui --host 0.0.0.0 --port 8765 --no-open`
2. Inform the user of the URL (e.g., http://<ip>:8765).

Note: This command blocks until stopped.