# APex IMM RCA Utility Release Notes

## Version 1.0.0 (Release Candidate)
**Release Date**: June 2026

### Features
- **Offline Log Analysis**: Process gigabytes of IMM logs instantly without cloud uploading.
- **Deep Learning Heuristics**: Automatically scan for 5xx errors, segmentation faults, and out-of-memory crashes in Redis/Sentinel/Nginx logs.
- **Incident Timeline**: Generate correlated mermaid sequence diagrams and detailed event logs.
- **Actionable Remediation**: Provide step-by-step resolution steps for recognized incidents.

### Fixes
- Added strict MAANG-grade formatting for incident reports to prevent markdown squashing.
- Auto-numbered Mermaid sequence diagrams that are now dynamically generated from log components (no hardcoded Redis references).
- Removed hardcoded local machine scanning for Magic installations; application now exclusively processes user-uploaded ZIPs.
- Standalone zero-dependency executable bundled via PyInstaller.
