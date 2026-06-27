import os
import json
import re
import hashlib
import subprocess

class RuleLearner:
    def __init__(self, rules_path=None, parser_config_path=None):
        if rules_path is None:
            rules_path = os.path.join("e:\\Tools\\imm-rca-utility", "backend", "config", "rules.json")
        if parser_config_path is None:
            parser_config_path = os.path.join("e:\\Tools\\imm-rca-utility", "backend", "config", "parser_config.json")
            
        self.rules_path = os.path.abspath(rules_path)
        self.parser_config_path = os.path.abspath(parser_config_path)

        # Common datetime patterns in logs
        # Maps raw regex -> (regex string for parser_config, format string)
        self.datetime_scanners = [
            # ISO variation: 2026-06-26 08:02:08
            (re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"), r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", "%Y-%m-%d %H:%M:%S"),
            # Slash ISO variation: 2026/06/26 08:02:08
            (re.compile(r"^\d{4}/\d{2}/\d{2}[T ]\d{2}:\d{2}:\d{2}"), r"^(\d{4}/\d{2}/\d{2}[T ]\d{2}:\d{2}:\d{2})", "%Y/%m/%d %H:%M:%S"),
            # Slash short variation: 26/06/2026 08:02:08
            (re.compile(r"^\d{2}/\d{2}/\d{4}[T ]\d{2}:\d{2}:\d{2}"), r"^(\d{2}/\d{2}/\d{4}[T ]\d{2}:\d{2}:\d{2})", "%d/%m/%Y %H:%M:%S"),
            # Common apache log bracket: [26/Jun/2026:08:02:08
            (re.compile(r"\[\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}"), r"\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2})", "%d/%b/%Y:%H:%M:%S")
        ]

    def learn_timestamp_formats(self, unparsed_lines: list) -> bool:
        """
        Scans a sample of unparsed lines. If it detects a recurring timestamp format that is not
        registered in parser_config.json, it automatically compiles a rule and registers it.
        """
        for line in unparsed_lines[:100]:
            line = line.strip()
            for scanner, regex_str, date_fmt in self.datetime_scanners:
                match = scanner.search(line)
                if match:
                    # Found a match! Check if this regex_str already exists in config
                    if self._register_parser_rule(regex_str, date_fmt):
                        print(f"Learned and registered new timestamp format: {date_fmt}")
                        return True
        return False

    def learn_error_rules(self, parsed_timeline: list) -> int:
        """
        Iterates over the parsed timeline. Identifies ERROR/CRITICAL logs that do not match
        any static/pre-existing rules, cleans up dynamic arguments, extracts signatures,
        clusters them, registers new rules in rules.json, and commits them to Git.
        """
        rules = self._load_rules()
        
        # Compile all existing pattern regexes
        compiled_regexes = []
        for r in rules:
            for p in r.get("patterns", []):
                try:
                    compiled_regexes.append(re.compile(p, re.IGNORECASE))
                except:
                    continue

        unknown_errors = []
        for entry in parsed_timeline:
            # We look for high severity items
            if entry.log_level in ["ERROR", "CRITICAL"]:
                # Check if it matches any existing rules
                matched = False
                for creg in compiled_regexes:
                    if creg.search(entry.message):
                        matched = True
                        break
                
                if not matched:
                    unknown_errors.append(entry.message)

        if not unknown_errors:
            return 0

        # Cluster and clean up signatures
        learned_rules_added = 0
        clusters = {}
        for err_msg in unknown_errors:
            cleaned = self._clean_signature(err_msg)
            clusters[cleaned] = clusters.get(cleaned, 0) + 1

        for signature, count in clusters.items():
            # Only learn patterns that repeat (or are significant)
            # For quick testing, we allow any signature length > 10 characters to become a rule
            if len(signature) < 10:
                continue
                
            # Create rule_id by hashing signature
            sig_hash = hashlib.md5(signature.encode('utf-8')).hexdigest()[:8]
            rule_id = f"LEARNED-ERR-{sig_hash.upper()}"
            
            # Check if this rule_id already exists in rules.json
            if any(r["rule_id"] == rule_id for r in rules):
                continue

            # Deduce rule name from signature
            name = self._deduce_rule_name(signature)
            
            # Deduce remediation tips
            remediation = self._deduce_remediation(signature)

            new_rule = {
                "rule_id": rule_id,
                "name": name,
                "severity": "ERROR",
                "patterns": [signature],
                "description": f"Auto-learned exception signature detected in logs. Occurred {count} times during incident analysis.",
                "remediation": remediation,
                "type": "learned"
            }
            rules.append(new_rule)
            learned_rules_added += 1

        if learned_rules_added > 0:
            self._save_rules(rules)
            self._commit_to_git(f"System Auto-Upgrade: Learned {learned_rules_added} new diagnostics rules")
            
        return learned_rules_added

    def _clean_signature(self, msg: str) -> str:
        # Helper to strip variable content like numbers, Hex addresses, PIDs, dates, paths
        cleaned = msg
        
        # 1. Strip time/date references in text (e.g. 2026-06-26 12:00:00)
        cleaned = re.sub(r"\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?", "", cleaned)
        
        # 2. Strip hex values: e.g. 0x7a06404f7cf3, [0x2f77e5a7]
        cleaned = re.sub(r"0x[0-9a-fA-F]+", "", cleaned)
        
        # 3. Strip numbers and IDs: e.g. WorkerData:1512, processId:3076, threadId:154514223951
        # Convert explicit key numbers to wildcards or generic matches
        cleaned = re.sub(r"\d+", "\\\\d+", cleaned)
        
        # 4. Escape special regex characters in the remaining static message
        # But preserve standard wildcards we just added
        escaped_parts = []
        for part in cleaned.split("\\\\d+"):
            escaped_parts.append(re.escape(part))
        cleaned = "\\\\d+".join(escaped_parts)
        
        # Collapse multiple spaces or multiple wildcards
        cleaned = re.sub(r"\s+", "\\s+", cleaned)
        return cleaned

    def _deduce_rule_name(self, signature: str) -> str:
        # Try to pull the exception name: e.g. ConnectionTimeoutException, NullPointerException
        match = re.search(r"([\w]+Exception|[\w]+Error)", signature)
        if match:
            return f"Learned Exception: {match.group(1)}"
            
        # Or parse the first 30 characters
        clean_name = re.sub(r"\\[\w\s]+", "", signature).strip()
        # Clean prefix text for name
        clean_name = clean_name[:40].strip()
        return f"Learned System Issue: {clean_name}..."

    def _deduce_remediation(self, signature: str) -> str:
        sig_lower = signature.lower()
        if "connect" in sig_lower or "socket" in sig_lower or "refused" in sig_lower or "timeout" in sig_lower:
            return "Verify target host availability, check security group firewall rules, and validate local IMM connection pools."
        if "memory" in sig_lower or "heap" in sig_lower or "oom" in sig_lower:
            return "Increase container resource bounds. Monitor heap allocation using jmap or visualvm."
        if "permission" in sig_lower or "denied" in sig_lower or "access" in sig_lower:
            return "Verify local OS folder file read/write permissions. Check active directory credential mappings."
        return "Review active flow runtime statistics, inspect trace logs for multi-line details, and check code parameters."

    def _load_rules(self) -> list:
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_rules(self, rules: list):
        try:
            with open(self.rules_path, 'w', encoding='utf-8') as f:
                json.dump(rules, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving rules: {e}")

    def _register_parser_rule(self, regex_str: str, date_fmt: str) -> bool:
        if not os.path.exists(self.parser_config_path):
            config = {"timestamp_rules": []}
        else:
            try:
                with open(self.parser_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                config = {"timestamp_rules": []}

        # Check if regex_str exists
        rules_list = config.get("timestamp_rules", [])
        if any(r["regex"] == regex_str for r in rules_list):
            return False

        pattern_id = f"LEARNED-DATE-{hashlib.md5(regex_str.encode('utf-8')).hexdigest()[:6].upper()}"
        rules_list.append({
            "pattern_id": pattern_id,
            "regex": regex_str,
            "format": date_fmt
        })
        config["timestamp_rules"] = rules_list
        
        try:
            with open(self.parser_config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self._commit_to_git(f"System Auto-Upgrade: Registered learned timestamp format {date_fmt}")
            return True
        except Exception as e:
            print(f"Error saving parser config: {e}")
        return False

    def _commit_to_git(self, commit_msg: str):
        try:
            # Change directory to E:\Tools\imm-rca-utility
            cwd = "E:\\Tools\\imm-rca-utility"
            
            # Run git add and commit
            subprocess.run(["git", "add", "backend/config/rules.json", "backend/config/parser_config.json"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Failed git auto-commit: {e}")
