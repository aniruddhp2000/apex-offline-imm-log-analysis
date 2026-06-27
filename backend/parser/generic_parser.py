import os
import json
import datetime
import re
import csv
from .base_parser import BaseLogParser, ParsedEntry

class GenericParser(BaseLogParser):
    def __init__(self, config_path=None):
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
            config_path = os.path.join(project_root, "backend", "config", "parser_config.json")
        self.config_path = os.path.abspath(config_path)
        
        # Compiled patterns loaded dynamically
        self.rules = []
        self.log4j_re = re.compile(
            r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:\+\d{2}:?\d{2})?)\s+(\w+)\s+([\w\.\$]+)\s+-\s+(.*)$"
        )
        self.ingress_re = re.compile(
            r"^\[([\d\.]+)\]\s+\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}\s+[\+\-]\d{4})\]\s+(\w+)\s+(\d{3})\s+(.*)$"
        )
        self._load_config()

    def _load_config(self):
        # Default fallback rules
        fallback_rules = [
            {
                "pattern_id": "ISO-DATETIME",
                "regex": r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:\.\d{3})?(?:[\+\-]\d{2}:?\d{2})?",
                "format": "%Y-%m-%d %H:%M:%S"
            },
            {
                "pattern_id": "APACHE-COMMON",
                "regex": r"\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2})(?:\s+[\+\-]\d{4})?\]",
                "format": "%d/%b/%Y:%H:%M:%S"
            }
        ]
        
        rules_list = []
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    rules_list = config.get("timestamp_rules", [])
            except Exception as e:
                print(f"Error loading parser configuration from {self.config_path}: {e}")
        
        if not rules_list:
            rules_list = fallback_rules
            
        self.rules = []
        for r in rules_list:
            try:
                self.rules.append({
                    "pattern_id": r["pattern_id"],
                    "regex": re.compile(r["regex"]),
                    "format": r["format"]
                })
            except Exception as e:
                print(f"Error compiling regex {r.get('regex')}: {e}")

    def parse(self, filepath: str, relative_path: str) -> list:
        # Re-load config dynamically to reflect self-learning updates
        self._load_config()

        # Check if it is an ALB CSV file
        if filepath.lower().endswith(".csv"):
            return self._parse_csv(filepath, relative_path)
            
        entries = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str:
                continue

            # Try Log4j match
            log4j_match = self.log4j_re.match(line_str)
            if log4j_match:
                ts_str, lvl, logger, msg = log4j_match.groups()
                dt = self._parse_date(ts_str)
                entries.append(ParsedEntry(
                    timestamp=dt,
                    log_level=lvl,
                    message=f"[{logger}] {msg}",
                    source_file=relative_path,
                    raw=line_str,
                    metadata={"logger": logger}
                ))
                continue

            # Try Ingress match
            ingress_match = self.ingress_re.match(line_str)
            if ingress_match:
                ip, ts_str, proto, status_code, rest = ingress_match.groups()
                dt = self._parse_date(ts_str)
                lvl = "ERROR" if status_code in ["500", "503", "502"] else "INFO"
                
                entries.append(ParsedEntry(
                    timestamp=dt,
                    log_level=lvl,
                    message=f"Access log: {proto} {status_code} - {rest}",
                    source_file=relative_path,
                    raw=line_str,
                    metadata={
                        "client_ip": ip,
                        "status_code": status_code,
                        "protocol": proto,
                        "type": "ingress"
                    }
                ))
                continue

            # Dynamic regex patterns from parser_config.json
            matched_fallback = False
            for rule in self.rules:
                match = rule["regex"].search(line_str)
                if match:
                    # We expect the first capturing group to hold the timestamp string
                    try:
                        ts_str = match.group(1)
                        # Extract rest of line (excluding the timestamp)
                        rest = line_str.replace(match.group(0), "").strip()
                        dt = self._parse_date(ts_str, rule["format"])
                        
                        # Guess log level
                        lvl = "INFO"
                        rest_upper = rest.upper()
                        if any(x in rest_upper for x in ["ERROR", "FATAL", "EXCEPTION", "SEVERE"]):
                            lvl = "ERROR"
                        elif "WARN" in rest_upper:
                            lvl = "WARNING"
                        elif "DEBUG" in rest_upper:
                            lvl = "DEBUG"
                            
                        entries.append(ParsedEntry(
                            timestamp=dt,
                            log_level=lvl,
                            message=rest if rest else line_str,
                            source_file=relative_path,
                            raw=line_str,
                            metadata={"pattern_id": rule["pattern_id"]}
                        ))
                        matched_fallback = True
                        break
                    except Exception as e:
                        # Continue if capture extraction fails
                        continue
            
            if matched_fallback:
                continue

            # If no timestamp matches, append to previous entry (multi-line stack traces)
            if entries:
                entries[-1].message += "\n" + line_str
                entries[-1].raw += "\n" + line_str
                # Elevate level if stack trace has exception/error
                if "exception" in line_str.lower() or "error" in line_str.lower() or "fatal" in line_str.lower():
                    entries[-1].log_level = "ERROR"

        return entries

    def _parse_csv(self, filepath: str, relative_path: str) -> list:
        entries = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for line_num, row in enumerate(reader, 1):
                    ts_str = row.get("report_timestamp", "")
                    if not ts_str:
                        continue
                    
                    dt = self._parse_date(ts_str)
                    resp_code = row.get("response_code", "")
                    srv_code = row.get("server_response_code", "")
                    client_ip = row.get("client_ip", "")
                    uri = row.get("uri_path", "")
                    method = row.get("method", "")
                    
                    code = resp_code or srv_code
                    lvl = "INFO"
                    if code in ["500", "502", "503", "504"]:
                        lvl = "ERROR"
                    
                    msg = f"HTTP {method} {uri} | Client: {client_ip} | Resp: {resp_code} | SrvResp: {srv_code}"
                    
                    metadata = {
                        "client_ip": client_ip,
                        "response_code": resp_code,
                        "server_response_code": srv_code,
                        "method": method,
                        "uri": uri,
                        "type": "alb_csv",
                        "line_num": line_num
                    }
                    
                    entries.append(ParsedEntry(
                        timestamp=dt,
                        log_level=lvl,
                        message=msg,
                        source_file=relative_path,
                        raw=str(row),
                        metadata=metadata
                    ))
        except Exception as e:
            print(f"Error parsing ALB CSV {filepath}: {e}")
        return entries

    def _parse_date(self, ts_str: str, fallback_fmt=None) -> datetime.datetime:
        ts_clean = ts_str.split('+')[0].split('-')[0].strip()
        ts_clean = ts_clean.replace('T', ' ')
        
        if '.' in ts_clean:
            ts_clean = ts_clean.split('.')[0]
            
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%d/%b/%Y:%H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d %b %Y %H:%M:%S"
        ]
        if fallback_fmt:
            formats.insert(0, fallback_fmt)
            
        for fmt in formats:
            try:
                return datetime.datetime.strptime(ts_clean, fmt)
            except:
                continue
        return datetime.datetime.utcnow()
