import os
import json
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Internal Imports
from backend.utils.workspace import WorkspaceManager
from backend.parser.file_discoverer import FileDiscoverer
from backend.parser.redis_parser import RedisParser
from backend.parser.generic_parser import GenericParser
from backend.analyzer.timeline_merger import TimelineMerger
from backend.analyzer.rca_heuristics import RCAHeuristics
from backend.analyzer.rule_learner import RuleLearner
from backend.utils.pdf_exporter import PDFExporter

app = FastAPI(title="Enterprise Log Diagnostic & RCA Hub")

workspace_mgr = WorkspaceManager()
discoverer = FileDiscoverer()
redis_parser = RedisParser()
generic_parser = GenericParser()
merger = TimelineMerger()
analyzer = RCAHeuristics()
learner = RuleLearner()

@app.post("/api/upload")
async def upload_logs(files: List[UploadFile] = File(...)):
    try:
        session_id = workspace_mgr.create_session()
        extracted_dir = workspace_mgr.get_extracted_dir(session_id)
        
        # Check if single zip uploaded, or a directory of files
        if len(files) == 1 and files[0].filename.endswith(".zip"):
            file = files[0]
            file_path = workspace_mgr.save_uploaded_file(session_id, file.filename, await file.read())
            workspace_mgr.extract_archive(session_id, file_path)
        else:
            # Handle directory / multiple files upload
            for file in files:
                # Reconstruct relative directory structure
                # filename will be e.g. "magic-xpi-imm-ns/sentinel.log" or "sentinel.log"
                # Secure filename path traversal check (ensure it is relative and inside extracted)
                rel_path = file.filename.replace("\\", "/")
                dest_path = os.path.join(extracted_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                content = await file.read()
                with open(dest_path, "wb") as f:
                    f.write(content)

        # Discover files in the workspace
        discovered = discoverer.discover_files(extracted_dir)
        
        # Self-Learning Step 1: Detect and register custom timestamp formats
        # Read the first few lines of generic log files that might not match standard formats
        sample_unparsed_lines = []
        for f_info in discovered:
            if f_info["category"] == "generic" and len(sample_unparsed_lines) < 200:
                try:
                    with open(f_info["path"], 'r', encoding='utf-8', errors='ignore') as sf:
                        sample_unparsed_lines.extend([sf.readline() for _ in range(20)])
                except:
                    pass
        if sample_unparsed_lines:
            learner.learn_timestamp_formats(sample_unparsed_lines)

        # Parse all discovered files
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
            
        # Merge timeline
        sorted_timeline = merger.merge(all_entries)
        
        # Self-Learning Step 2: Extract unrecognized errors and write new rules dynamically
        learned_count = learner.learn_error_rules(sorted_timeline)
        if learned_count > 0:
            print(f"Engine dynamically evolved: added {learned_count} new diagnostic rules.")

        # Run diagnostics (will load newly learned rules automatically)
        analysis_result = analyzer.analyze(sorted_timeline)
        
        # Serialize timeline
        serialized_timeline = [e.to_dict() for e in sorted_timeline]
        
        # Persist results in workspace folder
        session_dir = workspace_mgr.get_session_dir(session_id)
        
        with open(os.path.join(session_dir, "timeline.json"), "w", encoding="utf-8") as tf:
            json.dump(serialized_timeline, tf, indent=2, ensure_ascii=False)
            
        with open(os.path.join(session_dir, "rca_report.md"), "w", encoding="utf-8") as rf:
            rf.write(analysis_result["markdown_report"])
            
        with open(os.path.join(session_dir, "summary.json"), "w", encoding="utf-8") as sf:
            json.dump({
                "crashes_count": analysis_result["crashes_count"],
                "failovers_count": analysis_result["failovers_count"],
                "http_errors_count": analysis_result["http_errors_count"],
                "app_errors_count": analysis_result["app_errors_count"],
                "cycle_detected": analysis_result["cycle_detected"],
                "cycle_interval_seconds": analysis_result["cycle_interval_seconds"],
                "learned_rules_count": learned_count
            }, sf, indent=2, ensure_ascii=False)
            
        return {
            "session_id": session_id,
            "discovered_files": len(discovered),
            "total_log_entries": len(sorted_timeline),
            "crashes_detected": analysis_result["crashes_count"],
            "http_errors": analysis_result["http_errors_count"],
            "new_learned_rules": learned_count
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report/{session_id}")
async def get_report_data(session_id: str):
    session_dir = workspace_mgr.get_session_dir(session_id)
    md_path = os.path.join(session_dir, "rca_report.md")
    tl_path = os.path.join(session_dir, "timeline.json")
    sm_path = os.path.join(session_dir, "summary.json")
    
    if not (os.path.exists(md_path) and os.path.exists(tl_path)):
        raise HTTPException(status_code=404, detail="Session analysis not found.")
        
    with open(md_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
        
    with open(tl_path, 'r', encoding='utf-8') as f:
        timeline_data = json.load(f)
        
    with open(sm_path, 'r', encoding='utf-8') as f:
        summary_data = json.load(f)

    return {
        "markdown_report": markdown_content,
        "timeline": timeline_data,
        "summary": summary_data
    }

@app.get("/api/rules")
async def get_rules_database():
    rules_path = os.path.abspath("e:\\Tools\\imm-rca-utility\\backend\\config\\rules.json")
    if os.path.exists(rules_path):
        with open(rules_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@app.get("/api/download/markdown/{session_id}")
async def download_markdown(session_id: str):
    session_dir = workspace_mgr.get_session_dir(session_id)
    md_path = os.path.join(session_dir, "rca_report.md")
    if not os.path.exists(md_path):
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(
        md_path, 
        media_type="text/markdown", 
        filename=f"RCA_Report_{session_id}.md"
    )

@app.get("/api/download/pdf/{session_id}", response_class=HTMLResponse)
async def download_pdf(session_id: str):
    session_dir = workspace_mgr.get_session_dir(session_id)
    md_path = os.path.join(session_dir, "rca_report.md")
    if not os.path.exists(md_path):
        raise HTTPException(status_code=404, detail="Report not found.")
        
    with open(md_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
        
    html_report = PDFExporter.generate_html_report(f"RCA_Report_{session_id}", markdown_content)
    return html_report

# Serve Frontend Static Assets
frontend_dir = os.path.abspath("e:\\Tools\\imm-rca-utility\\frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
