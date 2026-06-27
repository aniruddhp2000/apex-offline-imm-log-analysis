import datetime
import re
from .base_parser import BaseLogParser, ParsedEntry

class RedisParser(BaseLogParser):
    def __init__(self):
        # Matches: pid:role date time.milliseconds level message
        # e.g., "8:M 25 Jun 2026 23:02:00.152 # Redis 6.2.13 crashed by signal: 11"
        # Or sentinel logs: "1:X 09 Jun 2026 12:56:13.878 * oO0OoO0OoO..."
        self.log_re = re.compile(
            r"^(\d+):([XMSC])\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+([.\-*#])\s+(.*)$"
        )
        # Fallback for timestamps without milliseconds
        self.log_no_ms_re = re.compile(
            r"^(\d+):([XMSC])\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2})\s+([.\-*#])\s+(.*)$"
        )

        # Level mapping
        self.level_map = {
            ".": "DEBUG",
            "-": "VERBOSE",
            "*": "INFO",
            "#": "ERROR"
        }

    def parse(self, filepath: str, relative_path: str) -> list:
        entries = []
        
        # Buffer for collecting crash logs / stack traces
        in_bug_report = False
        bug_report_buffer = []
        bug_report_start_idx = -1
        bug_report_ts = None
        bug_report_level = "ERROR"
        bug_report_pid = None
        bug_report_role = None

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            
            # Check for crash report boundary
            if "=== REDIS BUG REPORT START" in line_str:
                in_bug_report = True
                bug_report_buffer = [line_str]
                bug_report_start_idx = idx
                continue
            
            if in_bug_report:
                # If we hit the next valid log line with timestamp, or the end of the bug report
                # Note: some bug reports are long, but they typically don't have standard log headers inside them,
                # except occasionally some lines printed by the crash handler.
                # If we see "=== REDIS BUG REPORT END" or if we match a clean new log line, let's close the bug report.
                match = self.log_re.match(line_str) or self.log_no_ms_re.match(line_str)
                if match and ("crashed" not in line_str and "BUG REPORT" not in line_str):
                    # Close bug report and parse it
                    parsed_bug = self._process_bug_report(
                        bug_report_buffer, relative_path, bug_report_start_idx,
                        bug_report_ts, bug_report_level, bug_report_pid, bug_report_role
                    )
                    if parsed_bug:
                        entries.append(parsed_bug)
                    in_bug_report = False
                    bug_report_buffer = []
                else:
                    bug_report_buffer.append(line_str)
                    # Try to capture timestamp and metadata from the crash header lines
                    if match:
                        pid, role, dt_str, lvl_char, content = match.groups()
                        bug_report_pid = pid
                        bug_report_role = role
                        bug_report_ts = self._parse_timestamp(dt_str)
                        bug_report_level = self.level_map.get(lvl_char, "ERROR")
                    continue

            # Regular log line parsing
            match = self.log_re.match(line_str) or self.log_no_ms_re.match(line_str)
            if match:
                pid, role, dt_str, lvl_char, content = match.groups()
                dt = self._parse_timestamp(dt_str)
                lvl = self.level_map.get(lvl_char, "INFO")
                
                # Check for critical keywords to elevate log level
                if "crashed" in content.lower() or "segmentation fault" in content.lower():
                    lvl = "CRITICAL"
                elif "error" in content.lower() or "failed" in content.lower():
                    lvl = "ERROR"
                elif "warning" in content.lower():
                    lvl = "WARNING"
                
                metadata = {
                    "pid": pid,
                    "role": role, # X=Sentinel, M=Master, S=Slave, C=Child
                    "type": "redis" if role != "X" else "sentinel"
                }

                entries.append(ParsedEntry(
                    timestamp=dt,
                    log_level=lvl,
                    message=content,
                    source_file=relative_path,
                    raw=line_str,
                    metadata=metadata
                ))
            else:
                # If there is a random line, append it to the last parsed entry if available
                if entries and not in_bug_report:
                    entries[-1].message += "\n" + line_str
                    entries[-1].raw += "\n" + line_str

        # Flush any remaining bug report at EOF
        if in_bug_report and bug_report_buffer:
            parsed_bug = self._process_bug_report(
                bug_report_buffer, relative_path, bug_report_start_idx,
                bug_report_ts, bug_report_level, bug_report_pid, bug_report_role
            )
            if parsed_bug:
                entries.append(parsed_bug)

        return entries

    def _parse_timestamp(self, dt_str: str) -> datetime.datetime:
        # Standard: "%d %b %Y %H:%M:%S.%f"
        # Without MS: "%d %b %Y %H:%M:%S"
        # We need to support single-digit days like "9 Jun" or "09 Jun"
        # Python's strptime %d handles both, but %e is needed for space-padded on some platforms.
        # Let's clean up multiple spaces to simplify parsing.
        cleaned_dt = re.sub(r'\s+', ' ', dt_str)
        try:
            if "." in cleaned_dt:
                return datetime.datetime.strptime(cleaned_dt, "%d %b %Y %H:%M:%S.%f")
            else:
                return datetime.datetime.strptime(cleaned_dt, "%d %b %Y %H:%M:%S")
        except Exception as e:
            # Fallback current time if parsing fails
            return datetime.datetime.utcnow()

    def _process_bug_report(self, buffer: list, source_file: str, start_idx: int, default_ts, default_lvl, pid, role) -> ParsedEntry:
        raw_text = "\n".join(buffer)
        
        # Analyze buffer content
        message = "Redis Server Crash Report (Segmentation Fault / Signal 11)"
        stack_trace = []
        active_key = None
        crash_reason = None
        
        # Extract stack trace lines and key details
        for line in buffer:
            if "crashed by signal" in line:
                crash_reason = line.split("#")[-1].strip()
                message = f"Redis Server Crash: {crash_reason}"
            if "key '" in line and "found in DB" in line:
                active_key = line.split("key '")[-1].split("'")[0]
            # Stack trace frames typically start with module names/directories: e.g. /opt/redis-stack/lib/
            if ("/opt/redis-stack" in line or "redis-server" in line or "/lib/x86_64-linux" in line) and "[0x" in line:
                stack_trace.append(line.strip())

        # If we couldn't parse a timestamp from standard log lines, try to find one
        ts = default_ts if default_ts else datetime.datetime.utcnow()
        
        metadata = {
            "is_crash": True,
            "crash_reason": crash_reason,
            "active_key": active_key,
            "stack_trace": stack_trace,
            "pid": pid,
            "role": role,
            "type": "redis_crash",
            "start_line": start_idx
        }

        return ParsedEntry(
            timestamp=ts,
            log_level="CRITICAL",
            message=message,
            source_file=source_file,
            raw=raw_text,
            metadata=metadata
        )
