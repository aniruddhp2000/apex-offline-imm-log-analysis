# User Guide: Log Diagnostic & RCA Hub

Welcome to the **Enterprise Log Diagnostic & Root Cause Analysis (RCA) Hub**! This internal utility is designed for Support, R&D, and DevOps teams to quickly analyze log bundles and diagnose system issues (such as database crashes, Sentinel failovers, and HTTP error spikes).

---

## 1. Getting Started

### Prerequisites
* Python 3.8 or higher.
* Chrome, Edge, or Firefox browser.

### Installation & Launching
1. Open a terminal (PowerShell or Bash) and navigate to the project directory:
   ```bash
   cd E:\Tools\imm-rca-utility
   ```
2. Install the lightweight python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the application by running the batch script or starting uvicorn directly:
   * **Windows**: Run `run.bat`
   * **Any OS**:
     ```bash
     uvicorn backend.app:app --reload --port 8000
     ```
4. Open your browser and navigate to:
   ```
   http://localhost:8000/
   ```

---

## 2. Analyzing a Log Bundle

1. **Upload**: Drag and drop a `.zip` log archive directly onto the dashboard's central drop-zone. Alternatively, click the zone to browse and select a file.
2. **Dynamic Progress Tracking**: The upload indicator will display the progress across four distinct steps:
   * **Upload**: Transferring the archive to the local session workspace.
   * **Extract**: Unzipping all log folders (including nested zip archives).
   * **Parse**: Discovering log types and compiling log streams.
   * **Analyze**: Correlating timestamps and executing the RCA heuristics engine.
3. **Visual Dashboard**: Once completed, the interface will slide open to reveal the diagnostic dashboard.

---

## 3. Navigating the Diagnostic Workspace

The results workspace consists of three primary components:

### A. Metrics Bar
* **Crashes Detected**: Highlights database crashes. Glows red if any crashes are identified.
* **Sentinel Failovers**: Displays master election counts.
* **HTTP 5xx Errors**: Tracks client-facing request failures.
* **Log Entries**: Total logs aggregated into the unified stream.

### B. Interactive Chronological Timeline (Left Panel)
* **Filtering**: Use the filter buttons (`All`, `Crashes`, `Failovers`, `Errors`) at the top of the panel to isolate specific log event streams.
* **Inspecting Details**: Click on any event card in the timeline to expand the log details. This will reveal:
  * Event metadata (Source file path, Line numbers, Status codes).
  * The full, raw multi-line log message (e.g. database stack traces, registers, or exception dumps).
  * Click again to collapse the card.

### C. Investigation Report (Right Panel)
* **Markdown Viewer**: Displays the detailed, automated RCA report explaining the sequence of events, suspected triggers, and active database keys.
* **Mermaid.js Sequence Diagram**: High-fidelity system sequence diagrams render directly inside this panel to visualize the failover progression.
* **Exporting Reports**:
  * **Markdown**: Click the `Markdown` button at the top-right of the panel to download the standardized report file (`.md`).
  * **PDF**: Click the `PDF` button to open a print-preview tab. You can save the report as a PDF using your browser's print options (`Save as PDF`).

---

## 4. Resetting for a New Analysis

To analyze a new log bundle, click the **New Analysis** button at the top-right of the Investigation Report panel. This will clean the current dashboard state and return you to the upload screen.
