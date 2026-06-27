import os
import sys
from backend.utils.workspace import WorkspaceManager
from backend.parser.file_discoverer import FileDiscoverer
from backend.parser.redis_parser import RedisParser
from backend.parser.generic_parser import GenericParser
from backend.analyzer.timeline_merger import TimelineMerger
from backend.analyzer.rca_heuristics import RCAHeuristics

def main():
    print("Testing Log Diagnostic & RCA Utility Engine...")
    
    # Target zip file
    zip_path = r"e:\CASES\00135332\K8sPodLogs_2026-06-26_10-05-14.zip"
    if not os.path.exists(zip_path):
        print(f"Error: Target zip {zip_path} not found.")
        sys.exit(1)
        
    print(f"Loading log zip archive: {zip_path}")
    workspace_mgr = WorkspaceManager()
    session_id = workspace_mgr.create_session()
    print(f"Created temporary workspace session: {session_id}")
    
    # Save upload and extract
    dest_path = workspace_mgr.save_uploaded_file(session_id, os.path.basename(zip_path), open(zip_path, 'rb').read())
    extracted_dir = workspace_mgr.extract_archive(session_id, dest_path)
    print(f"Contents extracted to: {extracted_dir}")
    
    # Discover files
    discoverer = FileDiscoverer()
    discovered = discoverer.discover_files(extracted_dir)
    print(f"Discovered {len(discovered)} log files:")
    for f in discovered:
        print(f"  - [{f['category'].upper()}] {f['relative_path']}")
        
    # Parse streams
    redis_parser = RedisParser()
    generic_parser = GenericParser()
    all_entries = []
    
    for f_info in discovered:
        cat = f_info["category"]
        f_path = f_info["path"]
        rel_path = f_info["relative_path"]
        
        if cat in ["redis", "sentinel"]:
            entries = redis_parser.parse(f_path, rel_path)
        else:
            entries = generic_parser.parse(f_path, rel_path)
            
        all_entries.extend(entries)
        
    print(f"Parsed total {len(all_entries)} log entries.")
    
    # Merge and sort
    merger = TimelineMerger()
    sorted_timeline = merger.merge(all_entries)
    print(f"Unified chronological timeline compiled. Size: {len(sorted_timeline)}")
    
    # Run RCA Heuristics
    analyzer = RCAHeuristics()
    res = analyzer.analyze(sorted_timeline)
    
    print("\n================== RCA RESULTS SUMMARY ==================")
    print(f"Redis Process Crashes: {res['crashes_count']}")
    print(f"Sentinel Failovers:    {res['failovers_count']}")
    print(f"HTTP 5xx Errors:       {res['http_errors_count']}")
    print(f"Client App Errors:     {res['app_errors_count']}")
    print(f"Recurring Cycle Detected: {res['cycle_detected']}")
    if res['cycle_detected']:
        print(f"Interval: {res['cycle_interval_seconds']} seconds (~{int(res['cycle_interval_seconds']//60)} minutes)")
    print("=========================================================")
    
    # Print excerpt of the markdown report
    print("\nMarkdown Report Preview (First 20 lines):")
    print("\n".join(res['markdown_report'].split('\n')[:35]))
    
    # Clean workspace
    workspace_mgr.clean_session(session_id)
    print("\nTest completed successfully. Workspace cleaned.")

if __name__ == "__main__":
    main()
