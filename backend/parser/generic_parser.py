import datetime
import re
import csv
from .base_parser import BaseLogParser, ParsedEntry

class GenericParser(BaseLogParser):
    def __init__(self):
        # 1. Log4j/Logback format: e.g. "2026-06-26 08:02:08 ERROR c.m.m.serviceimpl.RedisHealthChecker - Error..."
        self.log4j_re = re.compile(
            r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:\+\d{2}:?\d{2})?)\s+(\w+)\s+([\w\.\$]+)\s+-\s+(.*)$"
        )
        
        # 2. Ingress Access log format: e.g. "[10.144.59.78] [26/Jun/2026:01:05:54 +0000] TCP 200 288 706 0.005"
        self.ingress_re = re.compile(
            r"^\[([\d\.]+)\]\s+\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}\s+[\+\-]\d{4})\]\s+(\w+)\s+(\d{3})\s+(.*)$"
        )

        # Generic date patterns for scanner fallback
        self.generic_date_patterns = [
            # ISO: 2026-06-26T08:02:08.123
            (re.compile(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{3})?)(.*)$"), "%Y-%m-%d %H:%M:%S"),
            # Common apache/ingress: 26/Jun/2026:08:02:08
            (re.compile(r"^(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2})(.*)$"), "%d/%b/%Y:%H:%M:%S"),
        ]

    def parse(self, filepath: str, relative_path: str) -> list:
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

            # Fallback regex patterns
            matched_fallback = False
            for pat, fmt in self.generic_date_patterns:
                f_match = pat.match(line_str)
                if f_match:
                    ts_str, rest = f_match.groups()
                    dt = self._parse_date(ts_str, fmt)
                    # Guess log level
                    lvl = "INFO"
                    rest_upper = rest.upper()
                    if "ERROR" in rest_upper or "FATAL" in rest_upper or "EXCEPTION" in rest_upper:
                        lvl = "ERROR"
                    elif "WARN" in rest_upper:
                        lvl = "WARNING"
                    elif "DEBUG" in rest_upper:
                        lvl = "DEBUG"
                        
                    entries.append(ParsedEntry(
                        timestamp=dt,
                        log_level=lvl,
                        message=rest.strip(),
                        source_file=relative_path,
                        raw=line_str
                    ))
                    matched_fallback = True
                    break
            
            if matched_fallback:
                continue

            # If no timestamp matches, append to previous entry (multi-line stack traces)
            if entries:
                entries[-1].message += "\n" + line_str
                entries[-1].raw += "\n" + line_str
                # Elevate level if stack trace has exception/error
                if "exception" in line_str.lower() or "error" in line_str.lower():
                    entries[-1].log_level = "ERROR"

        return entries

    def _parse_csv(self, filepath: str, relative_path: str) -> list:
        entries = []
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for line_num, row in enumerate(reader, 1):
                    # Check for required fields
                    ts_str = row.get("report_timestamp", "")
                    if not ts_str:
                        continue
                    
                    dt = self._parse_date(ts_str)
                    resp_code = row.get("response_code", "")
                    srv_code = row.get("server_response_code", "")
                    client_ip = row.get("client_ip", "")
                    uri = row.get("uri_path", "")
                    method = row.get("method", "")
                    
                    # Log errors for 5xx codes
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
        # Clean timezone offset: "26/Jun/2026:01:05:54 +0000" -> strip "+0000"
        ts_clean = ts_str.split('+')[0].split('-')[0].strip()
        ts_clean = ts_clean.replace('T', ' ')
        
        # Clean milliseconds suffix
        if '.' in ts_clean:
            ts_clean = ts_clean.split('.')[0]
            
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%d/%b/%Y:%H:%M:%S",
            "%Y/%m/%d %H:%M:%S"
        ]
        if fallback_fmt:
            formats.insert(0, fallback_fmt)
            
        for fmt in formats:
            try:
                return datetime.datetime.strptime(ts_clean, fmt)
            except:
                continue
        # Default fallback
        return datetime.datetime.utcnow()
