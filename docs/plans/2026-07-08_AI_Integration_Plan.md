# Enterprise Feature Implementation Plan: AI Integration & RCA Enhancements

As requested by the MAANG PM/Architect review, I've updated the architecture and feature set to give maximum flexibility and power to the end-user while maintaining enterprise security.

## Proposed Changes

### 1. Dynamic Session Title Extraction (History Title Fix)
We need to capture the exact name of the uploaded ZIP or folder so that the "History" tab displays it correctly instead of the hardcoded "Log Analysis".

#### [MODIFY] [app.py](file:///e:/Tools/imm-rca-utility/backend/app.py)
- Update `POST /api/upload`:
  - If a single zip is uploaded, extract its basename (e.g., `logs.zip` -> `logs`).
  - If a folder is uploaded, parse the first file's `webkitRelativePath` to extract the root folder name.
  - Pass this dynamically derived `session_name` into the `summary.json` generation block to replace the default "Log Analysis" string.

### 2. Explicit RCA Action Items (Offline Analysis)
We will elevate the remediation data from the rules engine into a highly visible, actionable checklist at the top of the Investigation Report.

#### [MODIFY] [rca_heuristics.py](file:///e:/Tools/imm-rca-utility/backend/analyzer/rca_heuristics.py)
- Modify `_build_markdown_report()`:
  - Aggregate the `remediation` fields from all *triggered* rules.
  - Create a new distinct section: `## 🎯 Actionable Remediation Plan`.
  - Format this section as a checklist (e.g., `- [ ] Action item...`) so engineers know exactly what to do first.

### 3. AI Co-Pilot Integration (OpenAI, Claude, Gemini, Microsoft)
We will introduce an extensible AI interface to perform deep, unstructured analysis on the offline RCA findings or the full raw logs.

#### [NEW] [ai_assistant.py](file:///e:/Tools/imm-rca-utility/backend/analyzer/ai_assistant.py)
- Create an extensible adapter class `AILogAnalyzer`.
- Implement provider clients using standard HTTP requests (to avoid heavy dependency management, or standard packages if preferred).
- **Context Handling**: The backend will accept a `context_mode` parameter:
  - `optimized`: Send `rca_report.md` + top 50 critical/error events.
  - `full`: Read and attach all extracted raw log files (concatenated, up to a reasonable hard limit to prevent OOM errors).

#### [MODIFY] [app.py](file:///e:/Tools/imm-rca-utility/backend/app.py)
- Add a new endpoint `POST /api/ai/analyze`:
  - Payload: 
    ```json
    { 
      "session_id": "str", 
      "provider": "str", 
      "model": "str", 
      "api_key": "str", 
      "context_mode": "optimized | full",
      "query": "str" 
    }
    ```

#### [MODIFY] [index.html](file:///e:/Tools/imm-rca-utility/frontend/index.html) & [app.css](file:///e:/Tools/imm-rca-utility/frontend/app.css)
- In the `#report-workspace`, add a "🤖 AI Co-Pilot" panel or modal.
- Form fields:
  - **Provider Dropdown**: OpenAI, Anthropic Claude, Google Gemini, Microsoft Azure OpenAI.
  - **Model Dropdown**: Dynamically populates based on provider:
    - *OpenAI*: gpt-4o, gpt-4-turbo, gpt-3.5-turbo
    - *Claude*: claude-3.5-sonnet, claude-3-opus, claude-3-haiku
    - *Gemini*: gemini-1.5-pro, gemini-1.5-flash
    - *Microsoft*: Custom Model Deployment Name (Input field)
  - **API Key**: Password field (Saved securely to `localStorage`).
  - **Context Toggle**: Radio buttons for "Optimized (Report + Top 50 Errors)" vs "Full Raw Logs (Warning: High Token Cost)".
  - **Custom Prompt**: Text area for specific questions.

#### [MODIFY] [app.js](file:///e:/Tools/imm-rca-utility/frontend/app.js)
- Add logic to handle the AI modal state, dropdown dependencies (Provider -> Models), and `localStorage` syncing.
- Add the `fetch` call to `/api/ai/analyze` and render the markdown response securely.

## Verification Plan
1. **Title Fix**: Upload a folder named `production-logs`. Go to History and verify it displays "production-logs".
2. **Action Items**: Upload logs that trigger errors and verify the offline report contains a `🎯 Actionable Remediation Plan`.
3. **AI Integration**: Open the AI modal, verify model dropdowns update correctly based on provider, select context mode, and verify the backend receives the correct payload.
