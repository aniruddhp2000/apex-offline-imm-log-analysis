# Walkthrough: APex Offline IMM Log Analysis

We have successfully executed the enterprise feature upgrade, completing the transformation into a premium, AI-powered diagnostic suite.

## What's New

### 1. 🤖 AI Co-Pilot Integration (OpenAI, Claude, Gemini, Azure)
The Investigation Report workspace now features a dedicated **AI Co-Pilot** modal, allowing you to run deep unstructured analysis on the offline log data.

- **Dynamic Model Selection**: Select your preferred provider (OpenAI, Anthropic Claude, Google Gemini, or Microsoft Copilot/Azure) and the UI will dynamically populate the compatible models (e.g., `gpt-4o`, `claude-3-5-sonnet-20240620`).
- **Secure Client-Side API Keys**: Your API keys are never hardcoded on the backend. They are securely saved in your browser's local storage and sent on-demand.
- **Context Toggle**: You can choose between:
  - **Optimized Context (Recommended)**: Sends the offline generated `rca_report.md` plus the top 50 critical/error timeline events. Fast and cheap.
  - **Full Raw Logs**: Sends the *entire* extracted raw log bundle for a massive contextual deep dive (Warning: Consumes a high amount of tokens).
- **Custom Queries**: Ask specific questions like, *"Why did the failover happen specifically at 10:45 AM?"*

### 2. 🎯 Actionable Remediation Checklist
The offline Investigation Report now aggregates all the scattered `remediation` advice from triggered rules and compiles them into a deduplicated, highly visible **Actionable Remediation Plan** checklist right at the top of the report. This ensures that engineers immediately know the next steps to resolve the detected anomalies.

### 3. Dynamic Session History Titles
The History table no longer shows "Log Analysis" for every upload. It now dynamically extracts the root folder name (e.g., `production-logs-july-8`) or the ZIP file name, making it infinitely easier to navigate past sessions.

### 4. APex Branding
The tool has been officially rebranded to **APex Offline IMM Log Analysis** across the UI, reflecting its premium, enterprise-grade capabilities.

---

## How to Test
1. **Restart the Backend**: Stop the currently running `.\run.bat` in your terminal and restart it.
2. **Refresh the Browser**: Reload `http://localhost:8000`.
3. **Upload an Archive**: Upload a folder of logs (ensure it triggers some errors/warnings).
4. **Verify Action Items**: Navigate to the **Analysis Report** tab and observe the new `🎯 Actionable Remediation Plan` checklist at the top.
5. **Test AI Co-Pilot**:
   - Click the new green **AI Co-Pilot** button in the top right of the report panel.
   - Enter your API Key for your preferred provider.
   - Click **Run Deep Analysis** and watch the LLM tear down the root cause!
