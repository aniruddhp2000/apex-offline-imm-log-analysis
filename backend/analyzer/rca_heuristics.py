import os
import json
import datetime
import re
from typing import List, Dict, Any
from backend.parser.base_parser import ParsedEntry

class RCAHeuristics:
    def __init__(self, rules_path=None):
        if rules_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
            rules_path = os.path.join(project_root, "backend", "config", "rules.json")
        self.rules_path = os.path.abspath(rules_path)
        self.rules = []
        self._load_rules()

    def _load_rules(self):
        self.rules = []
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, 'r', encoding='utf-8') as f:
                    rules_list = json.load(f)
                    for r in rules_list:
                        compiled_patterns = []
                        for p in r.get("patterns", []):
                            try:
                                compiled_patterns.append(re.compile(p, re.IGNORECASE))
                            except Exception as e:
                                print(f"Error compiling pattern {p}: {e}")
                        
                        self.rules.append({
                            "rule_id": r["rule_id"],
                            "name": r["name"],
                            "severity": r["severity"],
                            "description": r["description"],
                            "remediation": r["remediation"],
                            "type": r.get("type", "static"),
                            "compiled_patterns": compiled_patterns
                        })
            except Exception as e:
                print(f"Error loading rules from {self.rules_path}: {e}")

    def analyze(self, timeline: List[ParsedEntry]) -> Dict[str, Any]:
        # Re-load rules to fetch newly learned entries
        self._load_rules()

        crashes = []
        failovers = []
        http_errors = []
        app_errors = []
        
        # Track triggers of dynamic rules
        rules_trigger_counts = {r["rule_id"]: 0 for r in self.rules}
        rules_trigger_samples = {r["rule_id"]: [] for r in self.rules}
        
        for i, entry in enumerate(timeline):
            msg_lower = entry.message.lower()
            
            # 1. Standard structural Redis crash trace check (special handling for stack trace dumps)
            if entry.metadata.get("is_crash") or "crashed by signal" in msg_lower or "segmentation fault" in msg_lower:
                crashes.append({
                    "index": i,
                    "entry": entry,
                    "timestamp": entry.timestamp,
                    "file": entry.source_file,
                    "active_key": entry.metadata.get("active_key"),
                    "stack_trace": entry.metadata.get("stack_trace", [])
                })
                # Elevate level
                entry.log_level = "CRITICAL"
                
            # 2. Sentinel failover events (special handling)
            if entry.metadata.get("role") == "X" or "sentinel" in entry.source_file.lower():
                if any(x in msg_lower for x in ["+switch-master", "+sdown", "+odown", "+reboot", "failover-end"]):
                    failovers.append({
                        "index": i,
                        "entry": entry,
                        "timestamp": entry.timestamp,
                        "message": entry.message
                    })
            
            # 3. HTTP 5xx errors (special handling)
            is_http_5xx = False
            if entry.metadata.get("type") in ["alb_csv", "ingress"]:
                code = entry.metadata.get("response_code") or entry.metadata.get("server_response_code") or entry.metadata.get("status_code")
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
                entry.log_level = "ERROR"

            # 4. Check against all dynamic rules (both static and learned)
            for r in self.rules:
                matched = False
                for pattern in r["compiled_patterns"]:
                    if pattern.search(entry.message):
                        matched = True
                        break
                
                if matched:
                    # Update count and list
                    rules_trigger_counts[r["rule_id"]] += 1
                    if len(rules_trigger_samples[r["rule_id"]]) < 5:
                        rules_trigger_samples[r["rule_id"]].append(entry.message)
                    # Elevate log level if rule severity is high
                    if r["severity"] in ["ERROR", "CRITICAL"] and entry.log_level not in ["ERROR", "CRITICAL"]:
                        entry.log_level = r["severity"]
                        
            # Store generic app errors/exceptions
            if entry.log_level in ["ERROR", "CRITICAL"]:
                # Only append if not already classified as HTTP error
                if not is_http_5xx:
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
            
            correlated_http = []
            for err in http_errors:
                diff = abs((err["timestamp"] - crash_ts).total_seconds())
                if diff <= 180:
                    correlated_http.append(err)
                    
            correlated_sentinel = []
            for f in failovers:
                diff = abs((f["timestamp"] - crash_ts).total_seconds())
                if diff <= 180:
                    correlated_sentinel.append(f)

            correlated_app = []
            for err in app_errors:
                diff = abs((err["timestamp"] - crash_ts).total_seconds())
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

        # --- Recurring Pattern Check ---
        cycle_detected = False
        cycle_interval_seconds = 0
        if len(crashes) >= 2:
            intervals = []
            for idx in range(1, len(crashes)):
                diff = (crashes[idx]["timestamp"] - crashes[idx-1]["timestamp"]).total_seconds()
                intervals.append(diff)
            
            avg_interval = sum(intervals) / len(intervals)
            if all(abs(intv - avg_interval) < 45 for intv in intervals):
                cycle_detected = True
                cycle_interval_seconds = avg_interval

        # --- Build Diagnostics Report ---
        markdown_report = self._build_markdown_report(
            crashes, failovers, correlations, cycle_detected, cycle_interval_seconds,
            len(http_errors), rules_trigger_counts, rules_trigger_samples
        )

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

    def _build_markdown_report(self, crashes: list, failovers: list, correlations: list, cycle_detected: bool, cycle_interval: float, total_http_errs: int, trigger_counts: dict, trigger_samples: dict) -> str:
        report = []
        report.append("# Automated System Root Cause Analysis (RCA) Report")
        report.append(f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        # Executive Summary
        report.append("## Executive Summary")
        if crashes:
            report.append("> [!CRITICAL]\n"
                          f"> The engine identified **{len(crashes)} application process crashes** (SIGSEGV / Signal 11).\n"
                          f"> Load balancer logs recorded **{total_http_errs} HTTP 5xx client errors**.")
        else:
            report.append("> [!IMPORTANT]\n"
                          f"> No application process crashes were detected. However, **{total_http_errs} client-facing HTTP 5xx errors** were scanned.")

        # Incident Correlation
        if correlations:
            report.append("\n## Chronological Incident Correlation\n")
            for idx, corr in enumerate(correlations, 1):
                jst_time = corr["crash_time"] + datetime.timedelta(hours=9)
                report.append(f"### Incident Event #{idx}\n")
                report.append(f"* **UTC Time**: `{corr['crash_time'].strftime('%Y-%m-%d %H:%M:%S')}`")
                report.append(f"* **Local Time (JST)**: `{jst_time.strftime('%Y-%m-%d %H:%M:%S')}`")
                report.append(f"* **Crashed File Source**: `{corr['crash_file']}`")
                if corr["active_key"]:
                    report.append(f"* **Active Database Key**: `{corr['active_key']}`")
                report.append(f"* **Correlated Client HTTP Errors**: `{corr['http_errors_count']}` errors occurred during the failover transition.\n")
                
                if corr["stack_trace"]:
                    report.append("\n#### Stack Trace Header")
                    report.append("```")
                    for frame in corr["stack_trace"][:6]:
                        report.append(frame.strip())
                    report.append("```\n")
                    
                if corr.get("sentinel_events"):
                    report.append("#### Internal Event Progression\n")
                    report.append("| Event | Details |")
                    report.append("| :--- | :--- |")
                    for f in corr["sentinel_events"][:5]:
                        parts = f.strip().split(" ", 1)
                        # strictly format text to avoid breaking markdown tables
                        event = parts[0].replace('\n', '<br>').replace('|', '&#124;')
                        details = parts[1].replace('\n', '<br>').replace('|', '&#124;') if len(parts) > 1 else ""
                        report.append(f"| `{event}` | {details} |")
                    report.append("\n")
                report.append("---\n")

        if cycle_detected:
            mins = int(cycle_interval // 60)
            report.append("\n## Periodic / Cycle Pattern Analysis")
            report.append("> [!WARNING]\n"
                          f"> **Recurring Outage Cycle**: Failovers repeat at a regular interval of **{mins} minutes**.\n"
                          "> Suspect client-side scheduled job, sync loop, or cron utility triggers.")

        # Detected Issues Summary — only show rules that actually triggered
        triggered_rules = [r for r in self.rules if trigger_counts.get(r["rule_id"], 0) > 0]
        
        if triggered_rules:
            # Aggregate remediation action items
            report.append("\n## 🛠️ Actionable Remediation Plan")
            report.append("Based on the offline log analysis, the following actions are highly recommended to resolve the detected anomalies:\n")
            
            # Deduplicate remediations
            remediations = set()
            for r in triggered_rules:
                full_remedy = r.get("remediation", "").strip()
                if not full_remedy or full_remedy in remediations:
                    continue
                remediations.add(full_remedy)
                parts = full_remedy.split(". ")
                action = parts[0] + "." if parts else full_remedy
                reasoning = ". ".join(parts[1:]) if len(parts) > 1 else "Required to stabilize system state and prevent recurrence."
                
                report.append(f"### {r.get('name', 'General Action')}")
                report.append(f"* **Action**: {action}")
                report.append(f"* **Reasoning**: {reasoning}\n")
            
            if not remediations:
                report.append("- [ ] Investigate application logs further for undetected anomalies.")

            report.append("\n## Detected Issue Patterns")
            
            static_triggered = [r for r in triggered_rules if r["type"] != "learned"]
            learned_triggered = [r for r in triggered_rules if r["type"] == "learned"]
            
            total_rules = len(self.rules)
            report.append(f"The diagnostic engine evaluated logs against **{total_rules} detection rules** — "
                          f"**{len(triggered_rules)}** matched active issues in this dataset.\n")
            
            if static_triggered:
                report.append("### Known Issue Detections")
                for r in static_triggered:
                    count = trigger_counts[r["rule_id"]]
                    report.append(f"* **{r['name']}** ({r['severity']}) — Detected **{count}** occurrences")
                    if trigger_samples.get(r["rule_id"]):
                        report.append(f"  * Example: `{trigger_samples[r['rule_id']][0][:120]}`")
            
            if learned_triggered:
                report.append("\n### Newly Discovered Issue Patterns")
                report.append("The engine identified new unrecognized error signatures and automatically classified them:\n")
                for r in learned_triggered:
                    count = trigger_counts[r["rule_id"]]
                    report.append(f"#### {r['name']}")
                    report.append(f"* **Occurrences**: {count}")
                    report.append(f"* **Description**: {r['description']}")
                    report.append(f"* **Suggested Action**: {r['remediation']}")
                    if trigger_samples.get(r["rule_id"]):
                        report.append("* **Sample Traces**:")
                        report.append("  ```")
                        for sample in trigger_samples[r["rule_id"]][:2]:
                            report.append(f"  {sample}")
                        report.append("  ```")

        # Dynamic Sequence Diagram
        if correlations:
            report.append("\n## System Sequence Diagram\n")
            report.append("```mermaid\nsequenceDiagram\n    autonumber\n    participant Client as Client Apps / ALB\n    participant App as Application Process\n    participant System as Internal System\n")
            
            for idx, corr in enumerate(correlations, 1):
                safe_file = corr['crash_file'].replace('\n', ' ').replace('"', "'")
                report.append(f"    Note over App: Processing {safe_file}")
                report.append(f"    App->>App: Process exception or crash (Event #{idx})")
                
                if corr.get("sentinel_events"):
                    for f in corr["sentinel_events"][:3]:
                        # Strictly sanitize strings for mermaid parser
                        clean_event = f.strip().replace('\n', ' ').replace('"', "'").replace(';', ',')
                        if len(clean_event) > 45:
                            clean_event = clean_event[:42] + "..."
                        report.append(f"    System->>System: Log: {clean_event}")
                
                report.append("    Note over Client, App: Requests fail / HTTP 5xx logged")
                report.append("    App->>App: Process Restarted / Recovered")
            
            report.append("    Note over Client: Operations automatically resume\n```\n")

        return "\n".join(report)
