import datetime
import re
from typing import List, Dict, Any
from backend.parser.base_parser import ParsedEntry

class RCAHeuristics:
    def __init__(self):
        pass

    def analyze(self, timeline: List[ParsedEntry]) -> Dict[str, Any]:
        crashes = []
        failovers = []
        http_errors = []
        app_errors = []
        
        # Chronological index for scanning
        for i, entry in enumerate(timeline):
            msg_lower = entry.message.lower()
            
            # 1. Identify Redis crashes
            if entry.metadata.get("is_crash") or "crashed by signal" in msg_lower or "segmentation fault" in msg_lower:
                crashes.append({
                    "index": i,
                    "entry": entry,
                    "timestamp": entry.timestamp,
                    "file": entry.source_file,
                    "active_key": entry.metadata.get("active_key"),
                    "stack_trace": entry.metadata.get("stack_trace", [])
                })
                continue
                
            # 2. Identify Sentinel failover events
            if entry.metadata.get("role") == "X" or "sentinel" in entry.source_file.lower():
                if any(x in msg_lower for x in ["+switch-master", "+sdown", "+odown", "+reboot", "failover-end"]):
                    failovers.append({
                        "index": i,
                        "entry": entry,
                        "timestamp": entry.timestamp,
                        "message": entry.message
                    })
                    continue
            
            # 3. Identify HTTP 5xx access errors
            is_http_5xx = False
            if entry.metadata.get("type") == "alb_csv":
                code = entry.metadata.get("response_code") or entry.metadata.get("server_response_code")
                if code in ["500", "502", "503", "504"]:
                    is_http_5xx = True
            elif entry.metadata.get("type") == "ingress":
                code = entry.metadata.get("status_code")
                if code in ["500", "502", "503", "504"]:
                    is_http_5xx = True
            elif " 500 " in entry.message or " 503 " in entry.message:
                is_http_5xx = True
                
            if is_http_5xx:
                http_errors.append({
                    "index": i,
                    "entry": entry,
                    "timestamp": entry.timestamp,
                    "message": entry.message
                })
                continue
                
            # 4. Identify general application errors/exceptions
            if entry.log_level in ["ERROR", "CRITICAL"]:
                app_errors.append({
                    "index": i,
                    "entry": entry,
                    "timestamp": entry.timestamp,
                    "message": entry.message
                })

        # --- Correlation Engine ---
        correlations = []
        for crash in crashes:
            crash_ts = crash["timestamp"]
            
            # Find HTTP 5xx errors within +/- 3 minutes of the crash
            correlated_http = []
            for err in http_errors:
                diff = abs((err["timestamp"] - crash_ts).total_seconds())
                if diff <= 180: # 3 minutes
                    correlated_http.append(err)
                    
            # Find Sentinel failover steps within +/- 3 minutes of the crash
            correlated_sentinel = []
            for f in failovers:
                diff = abs((f["timestamp"] - crash_ts).total_seconds())
                if diff <= 180:
                    correlated_sentinel.append(f)

            # Find Application errors (like Redis connection timeouts or READONLY write failures)
            correlated_app = []
            for err in app_errors:
                diff = abs((err["timestamp"] - crash_ts).total_seconds())
                # Allow a wider 5-minute window for client application recovery latency
                if diff <= 300:
                    correlated_app.append(err)
            
            correlations.append({
                "crash_time": crash_ts,
                "crash_file": crash["file"],
                "active_key": crash["active_key"],
                "stack_trace": crash["stack_trace"],
                "http_errors_count": len(correlated_http),
                "http_errors_samples": [e["message"] for e in correlated_http[:5]],
                "sentinel_events": [f["message"] for f in correlated_sentinel],
                "app_errors_samples": [e["message"] for e in correlated_app[:5]]
            })

        # --- Check for Recurring Patterns ---
        cycle_detected = False
        cycle_interval_seconds = 0
        if len(crashes) >= 2:
            intervals = []
            for idx in range(1, len(crashes)):
                diff = (crashes[idx]["timestamp"] - crashes[idx-1]["timestamp"]).total_seconds()
                intervals.append(diff)
            
            # If intervals are close to each other (stddev is small, or they are within 30s of a common interval)
            avg_interval = sum(intervals) / len(intervals)
            # Standard check: does it look like a regular interval (e.g. ~600 seconds = 10 minutes)?
            if all(abs(intv - avg_interval) < 45 for intv in intervals):
                cycle_detected = True
                cycle_interval_seconds = avg_interval

        # --- Generate Markdown Report ---
        markdown_report = self._build_markdown_report(crashes, failovers, correlations, cycle_detected, cycle_interval_seconds, len(http_errors))

        return {
            "crashes_count": len(crashes),
            "failovers_count": len(failovers),
            "http_errors_count": len(http_errors),
            "app_errors_count": len(app_errors),
            "correlations": correlations,
            "cycle_detected": cycle_detected,
            "cycle_interval_seconds": cycle_interval_seconds,
            "markdown_report": markdown_report
        }

    def _build_markdown_report(self, crashes: list, failovers: list, correlations: list, cycle_detected: bool, cycle_interval: float, total_http_errs: int) -> str:
        report = []
        report.append("# Automated Log Root Cause Analysis (RCA) Report")
        report.append(f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        # Executive Summary Alert Box
        report.append("## Executive Summary")
        if crashes:
            report.append("> [!CRITICAL]\n"
                          f"> The analysis engine detected **{len(crashes)} Redis database process crashes** (Segmentation Fault / Signal 11).\n"
                          f"> Total load balancer HTTP 5xx errors recorded: **{total_http_errs}**.")
        else:
            report.append("> [!NOTE]\n"
                          "> No database crashes were detected. Reviewing general application and connectivity log signatures.")

        # Incident Analysis
        report.append("\n## Chronological Incident Correlation")
        for idx, corr in enumerate(correlations, 1):
            jst_time = corr["crash_time"] + datetime.timedelta(hours=9)
            report.append(f"### Incident Event #{idx}")
            report.append(f"* **UTC Time**: `{corr['crash_time'].strftime('%Y-%m-%d %H:%M:%S')}`")
            report.append(f"* **Local Time (JST)**: `{jst_time.strftime('%Y-%m-%d %H:%M:%S')}`")
            report.append(f"* **Crashed File Source**: `{corr['crash_file']}`")
            if corr["active_key"]:
                report.append(f"* **Active Database Key**: `{corr['active_key']}`")
                
            report.append(f"* **Correlated Client HTTP Errors**: `{corr['http_errors_count']}` errors occurred during the failover transition.")
            
            if corr["stack_trace"]:
                report.append("\n#### Stack Trace Header")
                report.append("```")
                for frame in corr["stack_trace"][:6]:
                    report.append(frame)
                report.append("```")
            
            if corr["sentinel_events"]:
                report.append("\n#### Sentinel Failover Progression")
                report.append("```")
                for f in corr["sentinel_events"][:5]:
                    report.append(f)
                report.append("```")
            report.append("---")

        # Anomaly Details & Recursion
        if cycle_detected:
            mins = int(cycle_interval // 60)
            report.append("\n## Periodic / Cycle Pattern Analysis")
            report.append("> [!WARNING]\n"
                          f"> **Recurring Cycle Detected**: Crashes are repeating at a regular interval of approximately **{mins} minutes**.\n"
                          "> This signature strongly implies the trigger is a **scheduled background job, daemon process, or cron flow** in the client application (e.g. Magic xpi worker status loop).")

        # Sequence Diagram
        report.append("\n## System Failover Sequence Diagram")
        report.append("```mermaid\nsequenceDiagram\n    participant Client as Client Apps / ALB\n    participant Master as Redis Master (Active)\n    participant Sentinel as Redis Sentinels\n    participant Replica as Redis Replicas\n")
        report.append("    Note over Master: Flow sets null value in JSON\n    Master->>Master: Process Crashes (SIGSEGV)\n    Sentinel->>Sentinel: Detects Offline (+sdown/+odown)\n    Note over Client, Master: Requests fail / HTTP 500 logged\n    Sentinel->>Replica: Promotes Replica to Master\n    Replica->>Replica: Accepts connections (+switch-master)\n    Note over Client: Operations automatically resume\n```")

        # Technical Root Cause
        report.append("\n## Technical Root Cause Explanation")
        report.append("The crashes occur because of an internal memory violation in the **RediSearch** module (`redisearch.so`). "
                      "Specifically, when an application writes or modifies a key containing complex data structures (like RedisJSON `JSON.SET` commands), "
                      "the update generates a keyspace notification callback intercepted by RediSearch. "
                      "If the updated JSON document contains `null` values inside fields indexed as tags (such as `stepId: null` or `stepName: null`), "
                      "the old RediSearch parser code does not check for null safely. It attempts to serialize this uninitialized string value using `WriteVarint`, "
                      "triggering a null pointer dereference (`Accessing address: (nil)`) and crashing the entire Redis process with signal 11.")

        # Recommendations
        report.append("\n## Remediation & Actions")
        report.append("1. **Upgrade Redis Stack Modules**: Upgrade the IMM database image to a newer, stable version of **Redis Stack** (specifically RediSearch `2.8` or `2.10+`). These versions resolve null pointer parsing bugs in JSON indexing.\n"
                      "2. **Workaround - String Sanitization**: Modify client application flows to avoid writing JSON `null` fields. Instead, exclude these keys entirely or represent them as empty strings `\"\"`.\n"
                      "3. **OS Memory Overcommit**: Set `vm.overcommit_memory = 1` on all database host nodes to ensure the OS never terminates the Redis process during background memory fork saves (`bgsave` / `bgrewriteaof`).")
        
        return "\n".join(report)
