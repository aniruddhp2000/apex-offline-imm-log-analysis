# Technical Architecture White Paper: Log Diagnostic & Root Cause Analysis Utility

**Document Ref**: FAANG-IMM-SAR-001  
**Author**: Antigravity Technical Systems Architect  
**Audience**: Support Operations, R&D Engineering, Devops  
**Status**: APPROVED / PRODUCTION-READY

---

## 1. Executive Summary & Vision

In cloud-native high-availability environments, localized node anomalies and silent microservice crashes can propagate rapidly, leading to complete production outages. The **Log Diagnostic & Root Cause Analysis (RCA) Utility** was built to address a key operational problem: reducing the Mean Time to Resolution (MTTR) for multi-node deployments. 

Rather than manually inspecting individual log streams, text trace files, and load balancer dumps, this tool introduces a unified platform. Users upload a log archive (ZIP file), and the backend automatically:
1. Extracts and structures all log streams recursively.
2. Identifies specific component log formats (Redis, Sentinel, Ingress, generic Log4j, etc.).
3. Merges all events into a unified, chronological timeline.
4. Evaluates anomalies and correlations using timeline sliding-window heuristics.
5. Builds a comprehensive, interactive visual dashboard and a standardized Markdown/PDF report.

---

## 2. Design Patterns & Modularity

The application was designed using **Clean Architecture** and SOLID design principles, maximizing code extensibility and maintainability.

```
+-------------------------------------------------------+
|                 Modern Glassmorphic UI                |
|           (index.html / app.css / app.js)             |
+---------------------------+---------------------------+
                            | REST API
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
        +-------------------+-------------------+
                            | Unified List[ParsedEntry]
+---------------------------v---------------------------+
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
   All log parsers inherit from the abstract class `BaseLogParser` (`backend/parser/base_parser.py`). When the discoverer identifies a file type (e.g. `redis`), it dynamically selects the corresponding parsing strategy (`RedisParser` or `GenericParser`). This allows Support engineers to easily register new parsers for other database or messaging queues (e.g. RabbitMQ, PostgreSQL) without touching core timeline merger or reporting logic.
2. **Singleton-style Lifecycle Management**:
   The `WorkspaceManager` manages sandbox directories. Every upload is assigned a standard UUID4 session, ensuring strict isolation between user uploads, preserving security, and preventing concurrent race conditions.

---

## 3. High-Performance Timeline Merging & Normalization

Logs from high-availability clusters often originate from disparate hosts configured in different timezones (e.g. container times in UTC and host syslogs or local customer reports in JST/GMT+9).

To solve this timezone delta issue:
* The parser converts incoming timestamps to neutral `datetime.datetime` objects.
* The `TimelineMerger` normalizes these timestamps to naive structures representing a unified epoch space and sorts them chronologically.
* When rendering the timeline, the frontend displays the unified UTC time alongside JST time (or local browser time) in parallel, allowing engineers to match logs precisely to the customer's reported incident window.

---

## 4. Anomaly Correlation Engine Heuristics

The `RCAHeuristics` engine executes structural correlation rules:
1. **Critical Node Signal Detector**:
   Scans the timeline for high-severity keywords (e.g. `crashed by signal`, `segmentation fault`). It isolates the exact crashing instruction address and extracts the active memory key (e.g. `key 'WorkerData:1512'`) from the hex dump.
2. **Failover Boundary Analyzer**:
   Tracks Sentinel failover commands (`+switch-master`, `+sdown`, `+odown`). It records the master-to-replica transition time.
3. **Sliding-Window Client Correlation**:
   Upon detecting a master crash, the engine opens a **+/- 3-minute sliding window**. It queries the timeline for correlated HTTP 5xx codes (Ingress/ALB) and database write connection errors (application logs) occurring within this window.
4. **Frequency Cycle Detector**:
   Evaluates timestamps between successive crash events. If the delta between crashes is uniform (e.g., standard deviation is low and averages ~10 minutes), the system flags a **recurring schedule trigger**—pointing Support to check for a periodic flow or cron job.

---

## 5. Architectural Trade-offs & Decisions

### Trade-off: Headless Browser PDF Generation vs. Browser-Native Print API
* **Decision**: We chose to implement a printable CSS layout (`@media print` rules inside `pdf_exporter.py` and `app.css`) that leverages the browser's native `window.print()` rendering engine, rather than integrating heavy PDF generation binaries (like `weasyprint`, `wkhtmltopdf`, or `puppeteer`).
* **Rationale**: Binary PDF generators have extensive OS library dependencies (Pango, Cairo, libc, etc.). Because this diagnostic tool is deployed internally and on support engineer laptops (running Windows, macOS, or Linux) and sometimes in air-gapped environments, shipping headless browser binaries would dramatically increase package size, complicate installations, and fail validation due to security policies. Browser-native printing is 100% portable, secure, and produces identical vector-quality PDFs.

### Trade-off: In-Memory Database vs. File-System Workspace Cache
* **Decision**: We opted for a stateless file-system cache where session timeline arrays and Markdown reports are saved inside `workspaces/<session_id>/` directories as JSON/Markdown files.
* **Rationale**: Memory-based caching is volatile; if the FastAPI server restarts, the user's active session is lost. By persisting session folders, the application remains lightweight, stateless (easily scalable behind load balancers), and users can download reports or load past sessions instantly without re-running the diagnostic CPU cycles.
