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
from backend.analyzer.ai_assistant import AILogAnalyzer
from backend.utils.pdf_exporter import PDFExporter

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

app = FastAPI(title="APex Offline IMM Log Analysis")

workspace_mgr = WorkspaceManager()
discoverer = FileDiscoverer()
redis_parser = RedisParser()
generic_parser = GenericParser()
merger = TimelineMerger()
analyzer = RCAHeuristics()
learner = RuleLearner()
ai_analyzer = AILogAnalyzer()

class AIRequest(BaseModel):
    session_id: str
    provider: str
    model: str
    api_key: str
    context_mode: str
    query: str = None



@app.post("/api/upload")
async def upload_logs(files: List[UploadFile] = File(...)):
    try:
        session_id = workspace_mgr.create_session()
        extracted_dir = workspace_mgr.get_extracted_dir(session_id)
        
        # Check if single zip uploaded, or a directory of files
        session_name = "Log Analysis"
        if len(files) == 1 and files[0].filename.endswith(".zip"):
            file = files[0]
            session_name = file.filename.replace(".zip", "")
            file_path = workspace_mgr.save_uploaded_file(session_id, file.filename, await file.read())
            workspace_mgr.extract_archive(session_id, file_path)
        else:
            # Handle directory / multiple files upload
            for file in files:
                # Reconstruct relative directory structure
                # Secure filename path traversal check (ensure it is relative and inside extracted)
                rel_path = file.filename.replace("\\", "/")
                
                # Extract root folder name for session title
                if session_name == "Log Analysis" and "/" in rel_path:
                    session_name = rel_path.split("/")[0]
                    
                dest_path = os.path.join(extracted_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                content = await file.read()
                with open(dest_path, "wb") as f:
                    f.write(content)

        # Discover files in the workspace
        discovered = discoverer.discover_files(extracted_dir)
        
        # Filter discovered files for relevance to accelerate parsing on large production bundles
        relevant_discovered = []
        filtered_count = 0
        for f_info in discovered:
            f_path = f_info["path"]
            f_name = f_info["filename"]
            
            is_relevant = False
            lower_name = f_name.lower()
            if "mgerror" in lower_name or "agent" in lower_name or "sentinel" in lower_name or "db" in lower_name or "ingress" in lower_name or f_info["category"] in ["redis", "sentinel", "ingress", "alb_csv"]:
                is_relevant = True
            else:
                size = f_info["size_bytes"]
                if size < 100 * 1024:  # Parse small files anyway
                    is_relevant = True
                else:
                    try:
                        # Quick check for error indicators in first and last 50KB
                        with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                            head = f.read(50 * 1024)
                            if size > 100 * 1024:
                                try:
                                    f.seek(size - 50 * 1024)
                                    tail = f.read()
                                except:
                                    tail = ""
                            else:
                                tail = ""
                            combined = (head + tail).lower()
                            keywords = ["error", "critical", "exception", "warn", "fail", "sdown", "odown", "fatal", "crash", "refused", "timeout"]
                            if any(kw in combined for kw in keywords):
                                is_relevant = True
                    except Exception as e:
                        print(f"Error checking relevance for {f_name}: {e}")
                        is_relevant = True
            
            if is_relevant:
                relevant_discovered.append(f_info)
            else:
                filtered_count += 1
                
        if filtered_count > 0:
            print(f"Production Optimizer: Filtered out {filtered_count} logs containing no error signatures to accelerate processing.")
        
        discovered = relevant_discovered
        
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
        
        # Filter and cap timeline for browser readability and performance (keep JSON size < 1MB)
        high_priority = []
        low_priority = []
        for entry in sorted_timeline:
            is_high = False
            # Prioritize CRITICAL/ERROR levels
            if entry.log_level in ["CRITICAL", "ERROR"] or entry.metadata.get("is_crash"):
                is_high = True
            # Prioritize sentinel state changes / failovers
            elif "sentinel" in entry.source_file.lower() and ("down" in entry.message.lower() or "switch" in entry.message.lower()):
                is_high = True
            # Prioritize rule matches
            elif entry.metadata.get("pattern_id"):
                is_high = True
                
            if is_high:
                high_priority.append(entry)
            else:
                low_priority.append(entry)
                
        # Limit total timeline entries to 5,000
        final_timeline = high_priority
        if len(final_timeline) < 5000:
            deficit = 5000 - len(final_timeline)
            if low_priority:
                # Sample low-priority entries evenly to maintain overall trace context
                step = max(1, len(low_priority) // deficit)
                sampled_low = low_priority[::step]
                final_timeline.extend(sampled_low[:deficit])
        else:
            # If high-priority alone exceeds 5,000, cap it at 10,000
            final_timeline = final_timeline[:10000]
            
        final_timeline.sort(key=lambda x: x.timestamp)
        sorted_timeline = final_timeline
        
        # Self-Learning Step 2: Extract unrecognized errors and write new rules dynamically
        learned_count = learner.learn_error_rules(sorted_timeline)
        if learned_count > 0:
            print(f"Engine dynamically evolved: added {learned_count} new diagnostic rules.")

        # Run diagnostics (will load newly learned rules automatically)
        analysis_result = analyzer.analyze(sorted_timeline)
        
        # Determine detected products
        detected_products = set()
        for f_info in discovered:
            rel_lower = f_info["relative_path"].lower()
            cat = f_info["category"]
            if cat in ["redis", "sentinel"] or "imm-db" in rel_lower or "sentinel" in rel_lower:
                detected_products.add("Magic IMM (In-Memory Middleware)")
            elif "mgerror" in rel_lower or "sql-log" in rel_lower or "xpa" in rel_lower:
                detected_products.add("Magic xpa (Application Platform)")
            elif "imm-agent" in rel_lower or "xpi" in rel_lower:
                detected_products.add("Magic xpi (Integration Platform)")
        
        if not detected_products:
            detected_products.add("Unknown System Log Stream")

        # Run diagnostics (will load newly learned rules automatically)
        analysis_result = analyzer.analyze(sorted_timeline)
        
        # Serialize timeline
        serialized_timeline = [e.to_dict() for e in sorted_timeline]
        
        # Persist results in workspace folder
        session_dir = workspace_mgr.get_session_dir(session_id)
        
        with open(os.path.join(session_dir, "timeline.json"), "w", encoding="utf-8") as tf:
            json.dump(serialized_timeline, tf, indent=2, ensure_ascii=False)
            
        with open(os.path.join(session_dir, "rca_report.md"), "w", encoding="utf-8") as rf:
            rf.write(analysis_result["markdown_report"] + "\n\n<div class=\"report-signature\">APex IMM RCA by Aniruddh Potdar</div>")
            
        import time
        with open(os.path.join(session_dir, "summary.json"), "w", encoding="utf-8") as sf:
            json.dump({
                "name": session_name,
                "timestamp": time.time(),
                "discovered_files": len(discovered),
                "crashes_count": analysis_result["crashes_count"],
                "failovers_count": analysis_result["failovers_count"],
                "http_errors_count": analysis_result["http_errors_count"],
                "app_errors_count": analysis_result["app_errors_count"],
                "cycle_detected": analysis_result["cycle_detected"],
                "cycle_interval_seconds": analysis_result["cycle_interval_seconds"],
                "learned_rules_count": learned_count,
                "detected_products": list(detected_products)
            }, sf, indent=2, ensure_ascii=False)
            
        return {
            "session_id": session_id,
            "discovered_files": len(discovered),
            "total_log_entries": len(sorted_timeline),
            "crashes_detected": analysis_result["crashes_count"],
            "http_errors": analysis_result["http_errors_count"],
            "new_learned_rules": learned_count,
            "detected_products": list(detected_products)
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def get_sessions():
    """
    Returns a list of past analysis sessions with metadata.
    """
    sessions = workspace_mgr.list_sessions()
    return {"sessions": sessions}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Deletes a specific analysis session and all its data.
    """
    workspace_mgr.clean_session(session_id)
    return {"status": "success", "message": f"Session {session_id} deleted."}

@app.get("/api/logs/{session_id}/file")
async def get_raw_log_file(session_id: str, path: str):
    """
    Returns the raw text content of a parsed log file.
    Security: prevents directory traversal by ensuring the requested file 
    is within the session's extracted directory.
    """
    extracted_dir = workspace_mgr.get_extracted_dir(session_id)
    if not os.path.exists(extracted_dir):
        raise HTTPException(status_code=404, detail="Session not found.")
        
    # Prevent path traversal
    clean_path = path.replace("\\", "/").strip("/")
    if ".." in clean_path:
        raise HTTPException(status_code=400, detail="Invalid path.")
        
    target_path = os.path.abspath(os.path.join(extracted_dir, clean_path))
    if not target_path.startswith(os.path.abspath(extracted_dir)):
        raise HTTPException(status_code=403, detail="Forbidden path.")
        
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail=f"Log file not found: {clean_path}")
        
    try:
        with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return HTMLResponse(content=content, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/analyze")
async def analyze_with_ai(req: AIRequest):
    """
    Sends the session context (either optimized report+errors or full logs) 
    to an external LLM for deep analysis.
    """
    session_dir = workspace_mgr.get_session_dir(req.session_id)
    if not os.path.exists(session_dir):
        raise HTTPException(status_code=404, detail="Session not found.")
        
    context = ""
    
    if req.context_mode == "full":
        # Full logs approach (can consume massive tokens)
        extracted_dir = workspace_mgr.get_extracted_dir(req.session_id)
        for root, _, files in os.walk(extracted_dir):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        context += f"\n\n--- FILE: {file} ---\n{f.read()}"
                except:
                    pass
        # Hard limit to ~200,000 chars to avoid complete memory/token blowout
        if len(context) > 200000:
            context = context[-200000:]
    else:
        # Optimized approach
        md_path = os.path.join(session_dir, "rca_report.md")
        tl_path = os.path.join(session_dir, "timeline.json")
        
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                context += f"\n--- OFFLINE RCA REPORT ---\n{f.read()}\n"
                
        if os.path.exists(tl_path):
            try:
                with open(tl_path, 'r', encoding='utf-8') as f:
                    tl_data = json.load(f)
                    
                # Get top 50 errors/criticals
                errors = [e for e in tl_data if e.get("log_level") in ["ERROR", "CRITICAL"]]
                context += "\n--- TOP 50 CRITICAL/ERROR TIMELINE EVENTS ---\n"
                for e in errors[:50]:
                    context += f"[{e['timestamp']}] {e['source_file']} | {e['message']}\n"
            except:
                pass
                
    if not context.strip():
        raise HTTPException(status_code=400, detail="No context could be generated for AI analysis.")
        
    try:
        response_md = ai_analyzer.analyze(
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
            context=context,
            query=req.query
        )
        
        signature = "\n\n<div class=\"report-signature\">APex IMM RCA by Aniruddh Potdar</div>"
        response_md += signature
        
        ai_report_path = os.path.join(session_dir, "ai_executive_summary.md")
        with open(ai_report_path, "w", encoding="utf-8") as f:
            f.write(response_md)
            
        return {"markdown_report": response_md}
    except Exception as e:
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

    ai_path = os.path.join(session_dir, "ai_executive_summary.md")
    ai_summary = None
    if os.path.exists(ai_path):
        with open(ai_path, 'r', encoding='utf-8') as f:
            ai_summary = f.read()

    return {
        "markdown_report": markdown_content,
        "timeline": timeline_data,
        "summary": summary_data,
        "ai_summary": ai_summary
    }

@app.get("/api/rules")
async def get_rules_database():
    rules_path = os.path.join(PROJECT_ROOT, "backend", "config", "rules.json")
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
frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
