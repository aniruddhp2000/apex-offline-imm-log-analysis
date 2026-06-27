import os
import sys
import shutil
import json
import traceback

# Calculate dynamic paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from backend.utils.workspace import WorkspaceManager
from backend.parser.file_discoverer import FileDiscoverer
from backend.parser.redis_parser import RedisParser
from backend.parser.generic_parser import GenericParser
from backend.analyzer.timeline_merger import TimelineMerger
from backend.analyzer.rule_learner import RuleLearner

def deep_scan():
    print("Initiating Deep Scan & Self-Learning loops...")
    
    # Target directories to scan
    scan_paths = [
        r"c:\Users\apotdar\Downloads",
        r"e:\CASES"
    ]
    
    workspace_mgr = WorkspaceManager()
    discoverer = FileDiscoverer()
    redis_parser = RedisParser()
    generic_parser = GenericParser()
    merger = TimelineMerger()
    learner = RuleLearner()

    total_learned = 0
    total_files_scanned = 0
    total_zips_processed = 0

    for path in scan_paths:
        if not os.path.exists(path):
            print(f"Directory not found, skipping: {path}")
            continue

        print(f"Scanning directory recursively: {path}")
        
        for root, dirs, files in os.walk(path):
            for file in files:
                lower_file = file.lower()
                fp = os.path.join(root, file)
                
                # Check for standard logs/errs
                if lower_file.endswith(".log") or lower_file.endswith(".err") or lower_file == "mgerror.log" or lower_file == "imm-agent.log":
                    try:
                        total_files_scanned += 1
                        # Copy file locally using our sharing lock bypass logic
                        lines = generic_parser._read_file_lines(fp)
                        if lines:
                            # Learn timestamp format first
                            learner.learn_timestamp_formats(lines)
                            
                            # Parse entries
                            entries = generic_parser.parse(fp, file)
                            if entries:
                                # Learn signatures
                                count = learner.learn_error_rules(entries)
                                if count > 0:
                                    total_learned += count
                                    print(f"  [LEARNED] {count} new rules from log file: {file}")
                    except Exception as e:
                        print(f"  Error reading log file {file}: {e}")
                
                # Check for zip archives containing log bundles
                elif lower_file.endswith(".zip"):
                    session_id = None
                    try:
                        total_zips_processed += 1
                        print(f"Processing Zip Archive: {file}")
                        session_id = workspace_mgr.create_session()
                        extracted_dir = workspace_mgr.get_extracted_dir(session_id)
                        
                        # Copy zip safely first in case of locks
                        temp_zip_dir = os.path.join(workspace_mgr.base_dir, "temp_zips")
                        os.makedirs(temp_zip_dir, exist_ok=True)
                        temp_zip_path = os.path.join(temp_zip_dir, f"temp_{session_id}.zip")
                        shutil.copyfile(fp, temp_zip_path)
                        
                        # Extract
                        workspace_mgr.extract_archive(session_id, temp_zip_path)
                        
                        # Clean temp zip file
                        if os.path.exists(temp_zip_path):
                            os.remove(temp_zip_path)
                            
                        # Discover log files in extracted archive
                        discovered = discoverer.discover_files(extracted_dir)
                        all_entries = []
                        
                        # Learn timestamps from discovered files first
                        scanned_lines = []
                        for f_info in discovered:
                            if len(scanned_lines) < 200:
                                try:
                                    lines = generic_parser._read_file_lines(f_info["path"])[:20]
                                    scanned_lines.extend(lines)
                                except:
                                    pass
                        if scanned_lines:
                            learner.learn_timestamp_formats(scanned_lines)

                        # Parse all files
                        for f_info in discovered:
                            cat = f_info["category"]
                            f_path = f_info["path"]
                            rel_path = f_info["relative_path"]
                            
                            try:
                                if cat in ["redis", "sentinel"]:
                                    entries = redis_parser.parse(f_path, rel_path)
                                else:
                                    entries = generic_parser.parse(f_path, rel_path)
                                all_entries.extend(entries)
                            except:
                                pass
                                
                        # Run learner on the merged entries
                        if all_entries:
                            count = learner.learn_error_rules(all_entries)
                            if count > 0:
                                total_learned += count
                                print(f"  [LEARNED] {count} new rules from zip archive: {file}")
                                
                        # Clean workspaces folder for session
                        workspace_mgr.clean_session(session_id)
                    except Exception as e:
                        if session_id:
                            workspace_mgr.clean_session(session_id)
                        print(f"  Error processing zip archive {file}: {e}")

    print(f"\n==================================================")
    print(f"DEEP SCAN COMPLETE SUMMARY:")
    print(f"Total Zip Archives Processed: {total_zips_processed}")
    print(f"Total Raw Log Files Scanned:   {total_files_scanned}")
    print(f"New Rules Dynamically Learned: {total_learned}")
    print(f"==================================================")

if __name__ == "__main__":
    deep_scan()
