# Technical Architecture White Paper: Log Diagnostic & Root Cause Analysis Utility

**Document Ref**: FAANG-IMM-SAR-001  
**Author**: Antigravity Technical Systems Architect  
**Audience**: Support Operations, R&D Engineering, DevOps  
**Status**: APPROVED / PRODUCTION-READY

---

## 1. Executive Summary & Vision

In cloud-native high-availability environments, localized node anomalies and silent microservice crashes can propagate rapidly, leading to complete production outages. The **Log Diagnostic & Root Cause Analysis (RCA) Utility** was built to address a key operational problem: reducing the Mean Time to Resolution (MTTR) for multi-node deployments.

This platform provides Support and R&D teams with a unified diagnostic interface. By dragging and dropping or browsing a log bundle (either a ZIP archive or a raw folder of files), users trigger an automatic, self-evolving analysis pipeline that:
1. Reconstructs file hierarchies for uploads.
2. Identifies and parses specialized log streams (Redis, Sentinel, Ingress, Log4j, etc.).
3. Merges all entries chronologically across timezone deltas.
4. Auto-detects anomalies, correlates crashes with client HTTP 500 error spikes, and calculates frequency cycles.
5. **Self-Learns and Self-Upgrades**: Dynamically scans for unrecognized log structures, extracts error signatures, registers new diagnostic rules, and commits rules updates automatically under a local Git repository.

---

## 2. Design Patterns & Modularity

The application is structured using **Clean Architecture** and SOLID design principles, maximizing code extensibility.

```
+-------------------------------------------------------+
|                 Modern Glassmorphic UI                |
|           (index.html / app.css / app.js)             |
+---------------------------+---------------------------+
                            | REST API (files/directories upload)
+---------------------------v---------------------------+
|                   FastAPI Router (app.py)             |
+---------------------------+---------------------------+
                            | Controller
+---------------------------v---------------------------+
|          Workspace & File Extractor (workspace.py)     |
+---------------------------+---------------------------+
                            | Scans & Discovers
+---------------------------v---------------------------+
|              File Discoverer (file_discoverer.py)     |
+---------------------------+---------------------------+
                            | Maps Parser Strategy
+---------------------------v---------------------------+
|                   BaseLogParser Interface             |
+-------+-------------------+-------------------+-------+
        |                   |                   |
+-------v-------+   +-------v-------+   +-------v-------+
|  RedisParser  |   | GenericParser |   | ...Future...  |
+-------+-------+   +-------+-------+   +-------+-------+
        |                   |                   |
        +---+---------------+---------------+
            |
            | List[ParsedEntry]
+-----------v-------------------------------------------+
|            AI Rule Learner (rule_learner.py)          |
|    - Timestamp Scanner -> updates parser_config.json  |
|    - Exception Clusterer -> updates rules.json        |
|    - Local Versioning -> Git Commit                   |
+-----------+-------------------------------------------+
            |
            | Evolved Configurations
+-----------v-------------------------------------------+
|             Timeline Merger (timeline_merger.py)      |
+---------------------------+---------------------------+
                            | Chronological List
+---------------------------v---------------------------+
|           RCA Heuristics Engine (rca_heuristics.py)   |
+---------------------------+---------------------------+
                            | Generates
+---------------------------v---------------------------+
|               Markdown & PDF Reports (pdf_exporter.py)|
+-------------------------------------------------------+
```

### Key Design Patterns Implemented
1. **Strategy Pattern (Log Parsing)**:
   All log parsers inherit from the abstract class `BaseLogParser`. When the discoverer identifies a file, it dynamically assigns the corresponding parsing strategy.
2. **Dynamic Database Configuration**:
   Heuristics rules are decoupled from Python code and placed in `backend/config/rules.json`. The generic parser timestamp configurations are managed via `backend/config/parser_config.json`. This database-driven design enables the utility to dynamically update its rule base at runtime.

---

## 3. Self-Evolving & Self-Upgrading Core Engine

The diagnostic engine is capable of **autonomous evolution** when encountering unrecognized log data:

### A. Dynamic Timestamp Pattern Discovery
If logs are parsed incorrectly because of unregistered dates formats (e.g. customized localization), the `RuleLearner` scans the first few lines of the text. It uses regex scanners to detect date/time prefixes, compiles the appropriate pattern, maps it to a Python datetime format, and appends it to `parser_config.json`. The parser immediately reload its config and parses the file, resolving parsing mismatches dynamically.

### B. Dynamic Exception Clustering
When the analysis engine scans a timeline, it isolates unrecognized `ERROR` or `CRITICAL` log statements that do not match any static rules in `rules.json`. It runs the following extraction pipeline:
1. **Variable Stripping**: Sanitizes strings by replacing dynamic parameters (hex codes, thread IDs, PIDs, date stamps, integer counters) with regex wildcards (e.g. `\d+`).
2. **Deduplication**: Clusters identical sanitized signatures and computes frequency counts.
3. **Rule Synthesizer**: Deduces a descriptive title (extracting exception class names like `TimeoutException` or base prefixes), maps a severity, outlines the pattern, and assigns default remediation tips (networking alerts for connection failures, memory flags for OOMs).
4. **Rules Upgrade**: Appends the new rule to `rules.json`.

### C. Local Version Control Tracking
Whenever `rules.json` or `parser_config.json` is modified by the learner, the utility executes an automated child process to commit the changes to the local Git repository:
```bash
git add backend/config/rules.json backend/config/parser_config.json
git commit -m "System Auto-Upgrade: Learned new diagnostics rules"
```
This ensures the utility logs all learned heuristics chronologically, preventing regressions and providing developer transparency.

---

## 4. Timezone Normalization & Cross-System Correlation

Logs from distributed clusters often span different timezones. The `TimelineMerger` normalizes timestamps into unified, naive datetime instances representing UTC. 

The correlation engine scans for database process crashes (SIGSEGV/signal 11). Once a crash is located, it evaluates a **+/- 3-minute sliding window** to identify correlated HTTP 500 error spikes from ingress logs and database write connection timeouts from application logs. This provides automated confirmation of client-facing impact without manual timeline overlay.

---

## 5. Architectural Trade-offs & Decisions

### Trade-off: Headless Browser PDF Generation vs. Browser-Native Print API
* **Decision**: We chose to implement a printable CSS layout (`@media print` rules) leveraging the browser's native `window.print()` rendering engine rather than Puppeteer/Weasyprint.
* **Rationale**:shipping browser binaries increases file sizes and triggers security warnings in corporate, air-gapped setups. Browser-native printing is secure, fast, and generates perfect vector PDFs.

### Trade-off: Local Git Tracking vs. Remote Configuration Server
* **Decision**: We chose to host a local Git repository inside the application workspace rather than pulling updates from a central database.
* **Rationale**: Support teams frequently operate in isolated customer networks without internet access. Local Git database updates ensure the utility remains fully operational, secure, and offline.
