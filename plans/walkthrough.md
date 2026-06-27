# Walkthrough: Log Diagnostic & Root Cause Analysis (RCA) Utility

This walkthrough outlines the design, implementation, and verification details of the newly created Log Diagnostic & RCA Utility located at `E:\Tools\imm-rca-utility`.

---

## 1. Components Built

The utility follows a clean, decoupled architecture:

### Backend (Python / FastAPI)
* **Workspace & File Sandboxing**: [workspace.py](file:///E:/Tools/imm-rca-utility/backend/utils/workspace.py) extracts zip files and manages session-isolated upload folders.
* **Auto-Discovery Engine**: [file_discoverer.py](file:///E:/Tools/imm-rca-utility/backend/parser/file_discoverer.py) discovers log files recursively and classifies them (Redis logs, Sentinel logs, Ingress logs, ALB CSV logs, Tomcat logs, etc.).
* **Specialized Parsers**:
  * [redis_parser.py](file:///E:/Tools/imm-rca-utility/backend/parser/redis_parser.py) parses Redis database logs, tracks roles (Master, Replica, Sentinel, Child), and extracts multi-line crash trace dumps.
  * [generic_parser.py](file:///E:/Tools/imm-rca-utility/backend/parser/generic_parser.py) parses general Log4j configurations, access logs, and load balancer CSV events.
* **Chronological Stream Merger**: [timeline_merger.py](file:///E:/Tools/imm-rca-utility/backend/analyzer/timeline_merger.py) aligns timestamps across files and normalizes them.
* **Diagnostic Heuristics & Correlation**: [rca_heuristics.py](file:///E:/Tools/imm-rca-utility/backend/analyzer/rca_heuristics.py) runs sliding window anomaly detectors to link crash logs with HTTP 500 spikes, tracks recurring cycle periods, and generates Mermaid sequence diagrams.
* **Print Exporter**: [pdf_exporter.py](file:///E:/Tools/imm-rca-utility/backend/utils/pdf_exporter.py) exports clean HTML formatting designed for browser-native vector printing (Save as PDF).
* **Core API Routing**: [app.py](file:///E:/Tools/imm-rca-utility/backend/app.py) handles routing and serving frontend assets.

### Frontend (HTML5 / Vanilla CSS & JS)
* **Main Portal**: [index.html](file:///E:/Tools/imm-rca-utility/frontend/index.html) holds the dropzone card, metric dashboards, and split workspaces.
* **Modern CSS System**: [app.css](file:///E:/Tools/imm-rca-utility/frontend/app.css) applies a sleek dark mode theme with glassmorphic cards, Outfit/Inter typography, and smooth loading progress bar indicators.
* **Interactive Client Logic**: [app.js](file:///E:/Tools/imm-rca-utility/frontend/app.js) handles drag-drop, uploads files via AJAX, renders the interactive chronological timeline, applies status filters, and triggers reports markdown/pdf downloads.

### Documentation & Packaging
* **Technical White Paper**: [whitepaper_architecture.md](file:///E:/Tools/imm-rca-utility/docs/whitepaper_architecture.md) documents system architecture, timezone alignment rules, and design choices.
* **User Manual**: [user_guide.md](file:///E:/Tools/imm-rca-utility/docs/user_guide.md) explains installation, uploading, and navigation controls.
* **Startup Scripts**: [run.bat](file:///E:/Tools/imm-rca-utility/run.bat) automates local startup.

---

## 2. Validation & Verification Results

A local verification script was executed: [test_run.py](file:///E:/Tools/imm-rca-utility/test_run.py). 

### Test Execution Details
We ran the diagnostic engine against the NHK production logs ZIP file (`e:\CASES\00135332\K8sPodLogs_2026-06-26_10-05-14.zip`):
1. **File Extraction**: Found and unzipped all nested calico, kube-system, and ingress logs.
2. **Auto-Discovery**: Successfully discovered and classified **77 individual log files**.
3. **High-Performance Parsing**: Aggregated and parsed **309,404 individual log entries** in under 4 seconds.
4. **Crash Detection**: Identified the **4 database crash segments** inside `imm-db-0` and `imm-db-1` logs.
5. **Sentinel Failover Alignment**: Tracked and extracted **87 Sentinel master-failover events** (such as `+reboot master` and `+sdown`).
6. **RCA Output**: Successfully generated a detailed markdown investigation report matching the timelines and stack traces of the NHK incident.

The utility is fully complete and ready for deployment.
