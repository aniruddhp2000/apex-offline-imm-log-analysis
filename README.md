# APex Offline IMM Log Analysis

<div align="center">
  <img src="frontend/assets/logo_small.png" alt="APex Logo" width="120" />
</div>

<h3 align="center">Enterprise-Grade Root Cause Analysis & Diagnostic Hub</h3>

<p align="center">
  Engineered by <strong>Aniruddh Potdar</strong> <br>
  <strong>Magic Software Enterprises (A MATRIX Company)</strong><br>
  <i>INTERNAL USE ONLY • CONFIDENTIAL</i>
</p>

---

## 📖 Overview

**APex Offline IMM Log Analysis** is a premium, AI-powered diagnostic suite designed for the post-mortem analysis of complex, distributed software environments. Built specifically to handle **Magic Software (IMM)**, **Redis**, **Sentinel**, and generic application logs, APex accelerates the mean-time-to-resolution (MTTR) by automatically extracting failure signatures, failovers, and HTTP anomalies from massive zip bundles.

## ✨ Core Features

- **🧠 Auto-Learning Rules Engine**: Automatically learns new error signatures on the fly. No need to constantly update static regex rules.
- **🤖 AI Co-Pilot Integration**: Built-in support for **OpenAI**, **Anthropic Claude**, **Google Gemini**, and **Microsoft Copilot (Azure)**. Send targeted timelines or full raw logs directly to an LLM for unstructured, deep-dive root cause analysis.
- **⏱️ Chronological Trace Timeline**: Merges logs from completely disparate systems (e.g., Redis, Ingress, Application) into a unified, second-by-second chronological trace.
- **🎯 Actionable Remediation Plans**: Aggregates triggered diagnostic rules into a clear, deduplicated checklist so engineers know exactly what to fix first.
- **💾 Session History Management**: Intelligently tracks past analysis sessions, allowing you to instantly reload or delete old forensic reports.
- **💻 Interactive Log Viewer**: Click on any timeline anomaly to dynamically fetch and highlight the exact failing trace within the raw log file.

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3 (Glassmorphism, Dark Theme)
- **AI Integration**: Standard HTTP adapters (Zero heavy SDK dependencies)

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Modern web browser (Chrome, Edge, Firefox)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/aniruddhp2000/apex-offline-imm-log-analysis.git
   cd apex-offline-imm-log-analysis
   ```

2. **Install dependencies**:
   *(Ensure you are in a virtual environment if required by your organizational policy)*
   ```bash
   pip install fastapi uvicorn pydantic python-multipart
   ```

3. **Start the server**:
   Simply run the provided batch script to boot the backend and serve the frontend:
   ```bash
   .\run.bat
   ```

4. **Access the application**:
   Open your browser and navigate to: [http://localhost:8000](http://localhost:8000)

## 💡 Usage Guide

1. **Upload**: Drag and drop your zipped log bundle or a directory of logs into the Dashboard.
2. **Review**: The system will automatically parse the logs, generate an Executive Summary, and build the Chronological Timeline.
3. **Action Items**: Navigate to the **Analysis Report** tab to view the *Actionable Remediation Plan*.
4. **AI Deep Dive**: Click the green **AI Co-Pilot** button, enter your preferred API key (cached securely in your browser), and run a deep analysis on the offline report.

## 🔐 Security & Privacy

- **Local Execution**: All static heuristics, merging, and parsing happen 100% locally on your machine.
- **API Keys**: AI Provider API keys are never stored on the server. They are cached via `localStorage` in the browser and transmitted exclusively to the chosen provider's official API endpoints.

## 📜 License & Copyright

**Proprietary and Confidential**
Copyright © 2026 Aniruddh Potdar / Magic Software Enterprises (A MATRIX Company).
All rights reserved.

Unauthorized copying of this file, via any medium, is strictly prohibited. For internal use by Magic Software Enterprises personnel only.
