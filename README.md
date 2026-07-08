<div align="center">
  <br>
  <img src="frontend/assets/logo.png" alt="APex Logo" width="350"/>
  <br><br>
  
  <h1>APex Offline IMM Log Analysis</h1>
  
  <p>
    <b>An Enterprise-Grade Root Cause Analysis & Diagnostic Hub for Distributed Systems</b>
  </p>

  <p>
    <a href="https://github.com/aniruddhp2000/apex-offline-imm-log-analysis/issues"><img src="https://img.shields.io/github/issues/aniruddhp2000/apex-offline-imm-log-analysis?style=for-the-badge&color=0098da" alt="Issues"></a>
    <a href="https://github.com/aniruddhp2000/apex-offline-imm-log-analysis/network/members"><img src="https://img.shields.io/github/forks/aniruddhp2000/apex-offline-imm-log-analysis?style=for-the-badge&color=0098da" alt="Forks"></a>
    <a href="https://github.com/aniruddhp2000/apex-offline-imm-log-analysis/stargazers"><img src="https://img.shields.io/github/stars/aniruddhp2000/apex-offline-imm-log-analysis?style=for-the-badge&color=a2238e" alt="Stars"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-Proprietary-red.svg?style=for-the-badge" alt="License"></a>
  </p>

  <p>
    <i>INTERNAL USE ONLY • CONFIDENTIAL</i>
  </p>
</div>

<hr>

## 📖 Overview

**APex Offline IMM Log Analysis** is a premium, AI-powered diagnostic suite designed for the post-mortem analysis of complex, distributed software environments. Built specifically to handle **Magic Software (IMM)**, **Redis**, **Sentinel**, and generic application logs, APex accelerates the mean-time-to-resolution (MTTR) by automatically extracting failure signatures, failovers, and HTTP anomalies from massive zip bundles.

---

## ✨ Features & Capabilities

<details>
<summary><b>🧠 Auto-Learning Rules Engine</b> (Click to expand)</summary>
<br>
Automatically learns new error signatures on the fly. No need to constantly update static regex rules. The engine intelligently classifies unhandled exceptions and adds them to its dynamic diagnostic arsenal.
</details>

<details>
<summary><b>🤖 AI Co-Pilot Integration</b></summary>
<br>
Built-in support for <b>OpenAI</b>, <b>Anthropic Claude</b>, <b>Google Gemini</b>, and <b>Microsoft Copilot (Azure)</b>. Send targeted timelines or full raw logs directly to an LLM for unstructured, deep-dive root cause analysis.
</details>

<details>
<summary><b>⏱️ Chronological Trace Timeline</b></summary>
<br>
Merges logs from completely disparate systems (e.g., Redis, Ingress, Application) into a unified, second-by-second chronological trace, eliminating the pain of manual timestamp correlation.
</details>

<details>
<summary><b>🎯 Actionable Remediation Plans</b></summary>
<br>
Aggregates triggered diagnostic rules into a clear, deduplicated checklist so support and engineering teams know exactly what to fix first.
</details>

<details>
<summary><b>💻 Interactive Log Viewer & History Management</b></summary>
<br>
Intelligently tracks past analysis sessions, allowing you to instantly reload or delete old forensic reports. Click on any timeline anomaly to dynamically fetch and highlight the exact failing trace within the raw log file.
</details>

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- A modern web browser (Chrome, Edge, Firefox)

### 2. Setup & Execution

```bash
# Clone the repository
git clone https://github.com/aniruddhp2000/apex-offline-imm-log-analysis.git
cd apex-offline-imm-log-analysis

# Install dependencies (use a virtual environment if preferred)
pip install fastapi uvicorn pydantic python-multipart

# Start the diagnostic server
.\run.bat
```

> **Note**: Once the server starts, navigate to [http://localhost:8000](http://localhost:8000) to access the APex Hub.

---

## 🔐 Privacy & Enterprise Security

- **Air-Gapped Execution**: All static heuristics, merging, and parsing happen 100% locally on your machine.
- **Secure AI Transport**: AI Provider API keys are **never** stored on the backend server. They are encrypted and cached locally via `localStorage` in your browser and transmitted exclusively to your chosen provider's official API endpoints on-demand.

---

## 👨‍💻 Author & Attribution

- **Created by**: Aniruddh Potdar (ITS-Support)
- **Company**: Magic Software Enterprises Ltd. (A MATRIX Company)
- **Copyright**: © 2026 Aniruddh Potdar. All rights reserved.

<div align="center">
  <sub>Built with ❤️ for Magic Software Enterprises</sub>
</div>
