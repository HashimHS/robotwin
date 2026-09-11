# Vendored BETR-XP-LLM

The behavior tree planner btvla runs on, copied here so `policy/btvla` has no
dependency outside the RobotWin tree.

- Source: <https://github.com/FaseehCS/BETR-XP-LLM> (fork of jstyrud/BETR-XP-LLM)
- Branch: `exp`
- Commit: `6b2ce05cc2a2b5498ef6d9c619bff53a0c78f52e`
- Synced: 2026-09-08

Only the modules btvla imports are vendored (`planner`, `behaviors`, `interfaces`,
`vlm`), byte for byte, so `diff -r` against an upstream checkout is meaningful. The
robot-specific interfaces and behaviors for ABB/RealSense/Thor are deliberately left
out.

## Refreshing

```bash
cd policy/btvla
./sync_vendor.sh [path/to/BETR-XP-LLM]     # defaults to ../../../betr_reflect/BETR-XP-LLM
```

Then update the commit and date above. Fix planner bugs upstream and re-sync rather
than editing the files here, so the two copies do not diverge.
