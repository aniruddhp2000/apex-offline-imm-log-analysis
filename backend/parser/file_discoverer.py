import os
import re
import csv

class FileDiscoverer:
    def __init__(self):
        # Compiled patterns to inspect the first few lines of a file
        self.redis_mode_re = re.compile(r"Running mode=(standalone|sentinel)")
        self.sentinel_event_re = re.compile(r"\+monitor master|\+sentinel sentinel|\+switch-master|\+sdown master")
        self.ingress_log_re = re.compile(r"\[\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\]\s+\[\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}")

    def discover_files(self, directory: str) -> list:
        discovered = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                fp = os.path.join(root, file)
                if not os.path.isfile(fp):
                    continue
                
                # Exclude obvious non-log/non-data formats
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.exe', '.dll', '.zip']:
                    continue

                category = self._classify_file(fp, file)
                discovered.append({
                    "path": os.path.abspath(fp),
                    "relative_path": os.path.relpath(fp, directory),
                    "filename": file,
                    "category": category,
                    "size_bytes": os.path.getsize(fp)
                })
        return discovered

    def _classify_file(self, filepath: str, filename: str) -> str:
        # Check by filename first
        lower_name = filename.lower()
        if "sentinel" in lower_name and lower_name.endswith(".log"):
            return "sentinel"
        if "imm-db" in lower_name and lower_name.endswith(".log"):
            return "redis"
        if "ingress-controller" in lower_name and lower_name.endswith(".log"):
            return "ingress"
        
        # Check if CSV is an ALB log
        if lower_name.endswith(".csv"):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read first line to check headers
                    header = f.readline()
                    if "report_timestamp" in header and "client_ip" in header and "response_code" in header:
                        return "alb_csv"
            except:
                pass
            return "generic_csv"

        # Content-based classification (first 50 lines)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content_sample = [f.readline() for _ in range(50)]
            
            merged_sample = "".join(content_sample)
            
            # Redis check
            if "Redis" in merged_sample and "crashed by signal" in merged_sample:
                return "redis"
            if self.redis_mode_re.search(merged_sample):
                if "mode=sentinel" in merged_sample:
                    return "sentinel"
                return "redis"
            if self.sentinel_event_re.search(merged_sample):
                return "sentinel"
                
            # Ingress check
            for line in content_sample:
                if self.ingress_log_re.search(line):
                    return "ingress"
        except Exception as e:
            print(f"Error inspecting {filepath} content: {e}")

        return "generic"
