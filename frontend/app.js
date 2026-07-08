document.addEventListener("DOMContentLoaded", () => {
    // State Variables
    let currentSessionId = null;
    let originalTimeline = [];
    let activeFilter = "all";

    // DOM Elements
    const logDropzone = document.getElementById("log-dropzone");
    const fileInput = document.getElementById("file-input");
    const folderInput = document.getElementById("folder-input");
    const uploadWorkspace = document.getElementById("upload-workspace");
    const timelineWorkspace = document.getElementById("timeline-workspace");
    const reportWorkspace = document.getElementById("report-workspace");
    const rulesWorkspace = document.getElementById("rules-workspace");
    const historyWorkspace = document.getElementById("history-workspace");
    const uploadProgressContainer = document.getElementById("upload-progress-container");
    const progressBar = document.getElementById("upload-progress-bar");
    const progressStatus = document.getElementById("progress-status");
    const progressPercentage = document.getElementById("progress-percentage");
    
    // Step indicators
    const stepUpload = document.getElementById("step-upload");
    const stepExtract = document.getElementById("step-extract");
    const stepParse = document.getElementById("step-parse");
    const stepAnalyze = document.getElementById("step-analyze");

    // Metrics
    const metricCrashes = document.getElementById("metric-crashes");
    const metricFailovers = document.getElementById("metric-failovers");
    const metricErrors = document.getElementById("metric-errors");
    const metricEntries = document.getElementById("metric-entries");

    // Navigation and Panels
    const navDashboardLink = document.getElementById("nav-dashboard-link");
    const navRulesLink = document.getElementById("nav-rules-link");
    const navTimelineLink = document.getElementById("nav-timeline-link");
    const navReportLink = document.getElementById("nav-report-link");
    const navHistoryLink = document.getElementById("nav-history-link");
    const navAiReportLink = document.getElementById("nav-ai-report-link");
    const timelineContainer = document.getElementById("timeline-container");
    const aiReportWorkspace = document.getElementById("ai-report-workspace");
    const aiReportContainer = document.getElementById("ai-report-container");
    const btnAiDownloadPdf = document.getElementById("btn-ai-download-pdf");
    const btnAiDownloadMd = document.getElementById("btn-ai-download-md");
    let currentAiMarkdown = "";
    const reportContainer = document.getElementById("report-container");
    const timelineSearch = document.getElementById("timeline-search");
    const historyListContainer = document.getElementById("history-list-container");
    const rulesListContainer = document.getElementById("rules-list-container");
    const rulesCount = document.getElementById("rules-count");
    
    // Log Viewer Elements
    const logViewerCode = document.getElementById("log-viewer-code");
    const logViewerTitle = document.getElementById("log-viewer-title");
    
    // Actions
    const btnBrowseFile = document.getElementById("btn-browse-file");
    const btnBrowseFolder = document.getElementById("btn-browse-folder");
    const btnDownloadPdf = document.getElementById("btn-download-pdf");
    const btnDownloadMd = document.getElementById("btn-download-md");
    const btnAnalyzeNew = document.getElementById("btn-analyze-new");

    // --- Init ---
    loadRulesDatabase();

    // Theme Switcher Init
    const savedTheme = localStorage.getItem("rca-theme") || "default-blue";
    setTheme(savedTheme);

    document.querySelectorAll(".theme-dot").forEach(dot => {
        dot.addEventListener("click", () => {
            const themeName = dot.getAttribute("data-theme");
            setTheme(themeName);
        });
    });

    function setTheme(themeName) {
        document.documentElement.setAttribute("data-theme", themeName);
        localStorage.setItem("rca-theme", themeName);
        
        document.querySelectorAll(".theme-dot").forEach(d => {
            if (d.getAttribute("data-theme") === themeName) {
                d.classList.add("active");
            } else {
                d.classList.remove("active");
            }
        });
    }

    // Prevent browser default drop behaviors globally
    window.addEventListener("dragover", (e) => {
        e.preventDefault();
    }, false);
    window.addEventListener("drop", (e) => {
        e.preventDefault();
    }, false);

    // --- Navigation ---
    // --- Navigation Handlers ---
    
    /**
     * Helper to hide all workspaces
     */
    function hideAllWorkspaces() {
        [uploadWorkspace, timelineWorkspace, reportWorkspace, aiReportWorkspace, rulesWorkspace, historyWorkspace].forEach(el => {
            if (el) el.classList.add("hidden");
        });
    }

    navDashboardLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (navDashboardLink.classList.contains("disabled")) return;
        switchNavigation(navDashboardLink);
        hideAllWorkspaces();
        resetUploadUI();
        uploadWorkspace.classList.remove("hidden");
    });

    navRulesLink.addEventListener("click", (e) => {
        e.preventDefault();
        switchNavigation(navRulesLink);
        hideAllWorkspaces();
        rulesWorkspace.classList.remove("hidden");
        loadRulesDatabase();
    });

    navHistoryLink.addEventListener("click", (e) => {
        e.preventDefault();
        switchNavigation(navHistoryLink);
        hideAllWorkspaces();
        historyWorkspace.classList.remove("hidden");
        loadHistory();
    });

    navTimelineLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (navTimelineLink.classList.contains("disabled")) return;
        switchNavigation(navTimelineLink);
        hideAllWorkspaces();
        timelineWorkspace.classList.remove("hidden");
        highlightPanel("panel-timeline");
    });

    navReportLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (navReportLink.classList.contains("disabled")) return;
        switchNavigation(navReportLink);
        hideAllWorkspaces();
        reportWorkspace.classList.remove("hidden");
        highlightPanel("panel-report");
    });

    navAiReportLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (navAiReportLink.classList.contains("disabled")) return;
        switchNavigation(navAiReportLink);
        hideAllWorkspaces();
        aiReportWorkspace.classList.remove("hidden");
        highlightPanel("panel-ai-report");
    });

    function highlightPanel(panelId) {
        const panel = document.getElementById(panelId);
        if (!panel) return;
        panel.classList.remove("panel-highlight");
        // Force reflow to restart animation
        void panel.offsetWidth;
        panel.classList.add("panel-highlight");
        panel.addEventListener("animationend", () => {
            panel.classList.remove("panel-highlight");
        }, { once: true });
    }

    function switchNavigation(activeLink) {
        document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
            item.classList.remove("active");
        });
        activeLink.classList.add("active");
    }

    // --- File & Folder Picker Uploads ---
    btnBrowseFile.addEventListener("click", (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    btnBrowseFolder.addEventListener("click", (e) => {
        e.stopPropagation();
        folderInput.click();
    });

    logDropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        logDropzone.classList.add("dragover");
    });

    logDropzone.addEventListener("dragleave", () => {
        logDropzone.classList.remove("dragover");
    });

    logDropzone.addEventListener("drop", async (e) => {
        e.preventDefault();
        logDropzone.classList.remove("dragover");
        
        const items = e.dataTransfer.items;
        if (items && items.length > 0) {
            let filesList = [];
            const promises = [];
            
            for (let i = 0; i < items.length; i++) {
                const entry = items[i].webkitGetAsEntry();
                if (entry) {
                    promises.push(traverseFileTree(entry).then(files => {
                        filesList = filesList.concat(files);
                    }));
                }
            }
            
            await Promise.all(promises);
            if (filesList.length > 0) {
                uploadFileList(filesList);
            }
        } else if (e.dataTransfer.files.length > 0) {
            handleFilesUpload(e.dataTransfer.files);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFilesUpload(e.target.files);
        }
    });

    folderInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFilesUpload(e.target.files);
        }
    });

    async function traverseFileTree(item, path = "") {
        if (item.isFile) {
            return new Promise((resolve) => {
                item.file((file) => {
                    resolve([{ file, path: path + file.name }]);
                });
            });
        } else if (item.isDirectory) {
            const dirReader = item.createReader();
            const entries = await new Promise((resolve) => {
                dirReader.readEntries((results) => resolve(results));
            });
            const filePromises = entries.map(entry => traverseFileTree(entry, path + item.name + "/"));
            const files = await Promise.all(filePromises);
            return files.flat();
        }
        return [];
    }

    function handleFilesUpload(fileList) {
        let list = [];
        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            const path = file.webkitRelativePath || file.name;
            list.push({ file, path });
        }
        uploadFileList(list);
    }

    function uploadFileList(filesList) {
        logDropzone.classList.add("hidden");
        uploadProgressContainer.classList.remove("hidden");
        updateProgress(10, "Uploading logs...", stepUpload);

        const formData = new FormData();
        
        filesList.forEach(item => {
            formData.append("files", item.file, item.path);
        });

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/upload", true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 40);
                updateProgress(percent, `Uploading log files (${percent}%)`, stepUpload);
            }
        };

        xhr.onload = function() {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                currentSessionId = response.session_id;

                setTimeout(() => {
                    updateProgress(60, "Scanning files & directories...", stepExtract);
                    setTimeout(() => {
                        updateProgress(80, "Running stream parsing and timestamps alignment...", stepParse);
                        setTimeout(() => {
                            let analyzeText = "Executing heuristics & self-learning dynamic rules...";
                            if (response.new_learned_rules > 0) {
                                analyzeText = `Self-evolved engine! Added ${response.new_learned_rules} new rules...`;
                            }
                            updateProgress(100, analyzeText, stepAnalyze);
                            setTimeout(() => {
                                loadReportResults(currentSessionId);
                                loadRulesDatabase();
                            }, 800);
                        }, 500);
                    }, 500);
                }, 500);
            } else {
                alert("Upload failed. Make sure the backend server is running correctly.");
                resetUploadUI();
            }
        };

        xhr.onerror = function() {
            alert("Connection error during upload.");
            resetUploadUI();
        };

        xhr.send(formData);
    }

    function updateProgress(percent, text, activeStep) {
        progressBar.style.width = `${percent}%`;
        progressPercentage.innerText = `${percent}%`;
        progressStatus.innerText = text;

        if (activeStep) {
            document.querySelectorAll(".step-indicator").forEach(s => s.classList.remove("active"));
            activeStep.classList.add("active");
            
            if (activeStep === stepExtract) {
                stepUpload.classList.add("complete");
            } else if (activeStep === stepParse) {
                stepUpload.classList.add("complete");
                stepExtract.classList.add("complete");
            } else if (activeStep === stepAnalyze) {
                stepUpload.classList.add("complete");
                stepExtract.classList.add("complete");
                stepParse.classList.add("complete");
            }
        }
    }

    function resetUploadUI() {
        logDropzone.classList.remove("hidden");
        uploadProgressContainer.classList.add("hidden");
        progressBar.style.width = `0%`;
        progressPercentage.innerText = `0%`;
        progressStatus.innerText = "Ready to upload";
        document.querySelectorAll(".step-indicator").forEach(s => {
            s.classList.remove("active", "complete");
        });
        stepUpload.classList.add("active");
        fileInput.value = "";
        folderInput.value = "";
        
        currentAiMarkdown = "";
        if (aiReportContainer) aiReportContainer.innerHTML = "";
        if (navAiReportLink) navAiReportLink.classList.add("hidden");
    }

    // --- Load analysis report from backend ---
    function loadReportResults(sessionId) {
        fetch(`/api/report/${sessionId}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch report data");
                return res.json();
            })
            .then(data => {
                document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("disabled"));
                
                metricCrashes.innerText = data.summary.crashes_count;
                metricFailovers.innerText = data.summary.failovers_count;
                metricErrors.innerText = data.summary.http_errors_count;
                metricEntries.innerText = data.timeline.length;

                if (data.summary.crashes_count > 0) {
                    metricCrashes.parentElement.parentElement.classList.add("critical");
                } else {
                    metricCrashes.parentElement.parentElement.classList.remove("critical");
                }

                // Display identified products list
                if (data.summary.detected_products && data.summary.detected_products.length > 0) {
                    const productsText = data.summary.detected_products.join(", ");
                    document.getElementById("main-subheading").innerHTML = `Identified Products: <strong>${productsText}</strong>`;
                }

                renderReport(data.markdown_report);

                originalTimeline = data.timeline;
                renderTimeline(originalTimeline);

                hideAllWorkspaces();
                reportWorkspace.classList.remove("hidden");
                switchNavigation(navReportLink);
                
                // Handle AI Summary if it exists in history
                if (data.ai_summary) {
                    currentAiMarkdown = data.ai_summary;
                    aiReportContainer.innerHTML = marked.parse(data.ai_summary);
                    navAiReportLink.classList.remove("hidden");
                }

                document.querySelector(".main-content").scrollTop = 0;
            })
            .catch(err => {
                console.error("Error loading results: ", err);
                alert("Error loading diagnostic results.");
                resetUploadUI();
            });
    }

    // --- Render Rules Knowledge base list ---
    function loadRulesDatabase() {
        fetch("/api/rules")
            .then(res => res.json())
            .then(rules => {
                rulesCount.innerText = `${rules.length} Active Rules`;
                rulesListContainer.innerHTML = "";
                
                if (rules.length === 0) {
                    rulesListContainer.innerHTML = `<div class="text-center text-muted" style="padding: 40px 0;">No active rules registered in database.</div>`;
                    return;
                }

                rules.forEach(rule => {
                    const node = document.createElement("div");
                    node.className = "rule-item";
                    
                    const isLearned = rule.type === "learned";
                    const typeText = isLearned ? "🤖 Self-Learned" : "System Static";
                    const typeClass = isLearned ? "learned" : "static";

                    const escapedPattern = escapeHtml(rule.patterns.join(" | "));

                    node.innerHTML = `
                        <div class="rule-header">
                            <div class="rule-title">
                                ${isLearned ? '🤖' : '⚙️'} ${escapeHtml(rule.name)}
                            </div>
                            <div class="rule-meta-badges">
                                <span class="rule-type-badge ${typeClass}">${typeText}</span>
                                <span class="rule-severity ${rule.severity}">${rule.severity}</span>
                            </div>
                        </div>
                        <div class="rule-desc">${escapeHtml(rule.description)}</div>
                        <div class="rule-pattern">Regex: <code>${escapedPattern}</code></div>
                        <div class="rule-remediation"><strong>Remediation:</strong> ${escapeHtml(rule.remediation)}</div>
                    `;
                    rulesListContainer.appendChild(node);
                });
            })
            .catch(err => console.error("Error loading rules base: ", err));
    }

    // --- Preprocess alert boxes & render Markdown ---
    function preprocessMarkdown(markdownText) {
        let md = markdownText;
        md = md.replace(/^>\s+\[!NOTE\]\s*\n((?:>.*\n?)*)/gim, (m, p1) => {
            const clean = p1.replace(/^>\s?/gm, '');
            return `<div class="alert alert-note">${clean}</div>`;
        });
        md = md.replace(/^>\s+\[!WARNING\]\s*\n((?:>.*\n?)*)/gim, (m, p1) => {
            const clean = p1.replace(/^>\s?/gm, '');
            return `<div class="alert alert-warning">${clean}</div>`;
        });
        md = md.replace(/^>\s+\[!CRITICAL\]\s*\n((?:>.*\n?)*)/gim, (m, p1) => {
            const clean = p1.replace(/^>\s?/gm, '');
            return `<div class="alert alert-critical">${clean}</div>`;
        });
        md = md.replace(/^>\s+\[!IMPORTANT\]\s*\n((?:>.*\n?)*)/gim, (m, p1) => {
            const clean = p1.replace(/^>\s?/gm, '');
            return `<div class="alert alert-important">${clean}</div>`;
        });
        
        // Ensure mermaid codeblocks are properly spaced (AI sometimes inlines them)
        md = md.replace(/([^\n])(```mermaid)/gi, "$1\n\n$2");
        md = md.replace(/(```)\s+([^\n])/g, "$1\n\n$2"); // Fix closing backticks
        
        return md;
    }

    function renderReport(markdownText) {
        const cleanMarkdown = preprocessMarkdown(markdownText);
        const parsedHtml = marked.parse(cleanMarkdown);
        reportContainer.innerHTML = parsedHtml;
        
        // Convert marked-parsed mermaid code blocks to div.mermaid safely
        const mermaidCodes = reportContainer.querySelectorAll('code.language-mermaid');
        mermaidCodes.forEach(code => {
            const div = document.createElement('div');
            div.className = 'mermaid';
            div.textContent = code.textContent; // Using textContent properly decodes marked's entities
            
            const pre = code.parentElement;
            if (pre && pre.tagName.toLowerCase() === 'pre') {
                pre.replaceWith(div);
            } else {
                code.replaceWith(div);
            }
        });
        
        try {
            mermaid.init(undefined, reportContainer.querySelectorAll(".mermaid"));
        } catch (e) {
            console.error("Error initializing mermaid: ", e);
        }
    }

    // --- Render Chronological Timeline list ---
    function renderTimeline(entries) {
        timelineContainer.innerHTML = "";
        
        let filtered = entries;
        if (activeFilter === "CRITICAL") {
            filtered = entries.filter(e => e.log_level === "CRITICAL" || e.log_level === "ERROR" && e.metadata.is_crash);
        } else if (activeFilter === "WARNING") {
            filtered = entries.filter(e => e.log_level === "WARNING" || e.source_file.toLowerCase().includes("sentinel"));
        } else if (activeFilter === "ERROR") {
            filtered = entries.filter(e => e.log_level === "ERROR");
        }

        const query = timelineSearch ? timelineSearch.value.toLowerCase() : "";
        if (query) {
            filtered = filtered.filter(e => {
                const ts = (e.timestamp || "").toLowerCase();
                const msg = (e.message || "").toLowerCase();
                const src = (e.source_file || "").toLowerCase();
                return ts.includes(query) || msg.includes(query) || src.includes(query);
            });
        }

        if (filtered.length === 0) {
            timelineContainer.innerHTML = `<div class="text-center text-muted" style="padding: 40px 0;">No log entries match the selected filter.</div>`;
            return;
        }

        filtered.forEach((entry, idx) => {
            const node = document.createElement("div");
            node.className = `timeline-node ${entry.log_level}`;
            
            let icon = '<box-icon name="info-circle" animation="tada-hover"></box-icon>';
            if (entry.log_level === "CRITICAL" || (entry.log_level === "ERROR" && entry.metadata.is_crash)) {
                icon = '<box-icon name="error" animation="flashing-hover"></box-icon>';
            } else if (entry.log_level === "ERROR") {
                icon = '<box-icon name="error-circle" animation="flashing-hover"></box-icon>';
            } else if (entry.log_level === "WARNING") {
                icon = '<box-icon name="transfer" animation="tada-hover"></box-icon>';
            }

            const dt = new Date(entry.timestamp);
            const tsStr = dt.toISOString().replace('T', ' ').substring(0, 19);

            node.innerHTML = `
                <div class="timeline-indicator">${icon}</div>
                <div class="timeline-content" id="tl-node-${idx}">
                    <div class="timeline-meta">
                        <span class="timeline-time">${tsStr} UTC</span>
                        <span class="timeline-src" title="${entry.source_file}">${entry.source_file}</span>
                    </div>
                    <div class="timeline-msg">${escapeHtml(entry.message)}</div>
                </div>
            `;
            
            node.querySelector(".timeline-content").addEventListener("click", () => {
                // Remove active styling from all other nodes
                document.querySelectorAll(".timeline-node").forEach(n => n.classList.remove("active-node"));
                node.classList.add("active-node");
                
                logViewerTitle.innerText = `Loading ${entry.source_file}...`;
                logViewerCode.innerHTML = "Fetching raw log data...";
                
                // Fetch the raw log file from the server
                fetch(`/api/logs/${currentSessionId}/file?path=${encodeURIComponent(entry.source_file)}`)
                    .then(res => {
                        if (!res.ok) throw new Error("Could not load log file.");
                        return res.text();
                    })
                    .then(text => {
                        logViewerTitle.innerHTML = `<box-icon name="code-block" animation="tada-hover"></box-icon> ${escapeHtml(entry.source_file)}`;
                        
                        // Use string matching to highlight the exact log line
                        // The 'raw' attribute was added to the backend ParsedEntry.to_dict
                        if (entry.raw && text.includes(entry.raw)) {
                            const escapedRaw = escapeHtml(entry.raw);
                            const escapedText = escapeHtml(text);
                            const highlightedText = escapedText.replace(
                                escapedRaw, 
                                `<span class="log-highlight" id="active-log-line">${escapedRaw}</span>`
                            );
                            logViewerCode.innerHTML = highlightedText;
                            
                            // Scroll to highlight
                            setTimeout(() => {
                                const highlightEl = document.getElementById("active-log-line");
                                if (highlightEl) {
                                    highlightEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                }
                            }, 100);
                        } else {
                            logViewerCode.innerHTML = escapeHtml(text);
                        }
                    })
                    .catch(err => {
                        console.error("Error loading raw log: ", err);
                        logViewerCode.innerHTML = `<span style="color:var(--accent-red)">Error: ${err.message}</span>`;
                    });
            });

            timelineContainer.appendChild(node);
        });
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // --- Timeline filter controls ---
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            activeFilter = e.target.getAttribute("data-filter");
            renderTimeline(originalTimeline);
        });
    });

    if (timelineSearch) {
        timelineSearch.addEventListener("input", () => {
            renderTimeline(originalTimeline);
        });
    }

    /**
     * Fetch and render past analysis sessions from the backend
     */
    function loadHistory() {
        historyListContainer.innerHTML = `<div class="text-center text-muted" style="padding: 40px 0;"><box-icon name="loader-alt" animation="spin"></box-icon> Loading history...</div>`;
        
        fetch("/api/sessions")
            .then(res => res.json())
            .then(data => {
                if (!data.sessions || data.sessions.length === 0) {
                    historyListContainer.innerHTML = `<div class="text-center text-muted" style="padding: 40px 0;">No previous analysis sessions found.</div>`;
                    return;
                }
                
                let tableHtml = `
                    <table class="history-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Title</th>
                                <th>Files</th>
                                <th>Crashes</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                data.sessions.forEach(session => {
                    const dt = new Date(session.timestamp * 1000).toLocaleString();
                    tableHtml += `
                        <tr>
                            <td>${dt}</td>
                            <td>${escapeHtml(session.name)}</td>
                            <td>${session.file_count}</td>
                            <td><span class="${session.crashes > 0 ? 'rule-severity CRITICAL' : ''}">${session.crashes}</span></td>
                            <td class="history-actions">
                                <button class="action-btn primary" onclick="window.loadHistoricalSession('${session.session_id}')">Load</button>
                                <button class="action-btn danger" onclick="window.deleteSession('${session.session_id}')">Delete</button>
                            </td>
                        </tr>
                    `;
                });
                
                tableHtml += `</tbody></table>`;
                historyListContainer.innerHTML = tableHtml;
            })
            .catch(err => {
                console.error("Error loading history: ", err);
                historyListContainer.innerHTML = `<div class="text-center" style="padding: 40px 0; color: var(--accent-red)">Error loading history.</div>`;
            });
    }

    // Expose functions to window for onclick handlers in the HTML string
    window.loadHistoricalSession = (sessionId) => {
        currentSessionId = sessionId;
        loadReportResults(sessionId);
    };

    window.deleteSession = (sessionId) => {
        if (!confirm("Are you sure you want to delete this analysis session?")) return;
        fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(data => {
                if (currentSessionId === sessionId) {
                    currentSessionId = null;
                }
                loadHistory(); // refresh table
            })
            .catch(err => alert("Error deleting session"));
    };

    // --- Actions Handlers ---
    btnDownloadMd.addEventListener("click", () => {
        if (!currentSessionId) return;
        window.open(`/api/download/markdown/${currentSessionId}`, "_blank");
    });

    btnDownloadPdf.addEventListener("click", () => {
        if (!currentSessionId) return;
        window.open(`/api/download/pdf/${currentSessionId}`, "_blank");
    });

    btnAnalyzeNew.addEventListener("click", () => {
        currentSessionId = null;
        originalTimeline = [];
        resetUploadUI();
        hideAllWorkspaces();
        uploadWorkspace.classList.remove("hidden");
        switchNavigation(navDashboardLink);
        document.querySelectorAll(".sidebar-nav .nav-item").forEach(el => {
            if (el.id === "nav-timeline-link" || el.id === "nav-report-link") {
                el.classList.add("disabled");
            }
        });
        document.getElementById("main-subheading").innerText = "Upload offline log bundles to initiate multi-system trace and anomaly detection.";
    });

    // --- AI Co-Pilot Logic ---
    const btnAiCopilot = document.getElementById("btn-ai-copilot");
    const aiModal = document.getElementById("ai-modal");
    const closeAiModal = document.getElementById("close-ai-modal");
    
    const aiProvider = document.getElementById("ai-provider");
    const aiModel = document.getElementById("ai-model");
    const aiModelCustom = document.getElementById("ai-model-custom");
    const aiApiKey = document.getElementById("ai-api-key");
    const aiQuery = document.getElementById("ai-query");
    const btnRunAi = document.getElementById("btn-run-ai");
    const aiResults = document.getElementById("ai-results");

    const MODEL_MAP = {
        "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "claude": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash"]
    };

    function updateAiModels() {
        const provider = aiProvider.value;
        aiModel.innerHTML = "";
        
        if (provider === "microsoft") {
            aiModel.classList.add("hidden");
            aiModelCustom.classList.remove("hidden");
        } else {
            aiModelCustom.classList.add("hidden");
            aiModel.classList.remove("hidden");
            
            const models = MODEL_MAP[provider] || [];
            models.forEach(m => {
                const opt = document.createElement("option");
                opt.value = m;
                opt.innerText = m;
                aiModel.appendChild(opt);
            });
        }
        
        // Load saved API key for provider
        const savedKey = localStorage.getItem(`imm_ai_key_${provider}`);
        if (savedKey) {
            aiApiKey.value = savedKey;
        } else {
            aiApiKey.value = "";
        }
    }

    if(btnAiCopilot) {
        btnAiCopilot.addEventListener("click", () => {
            aiModal.classList.remove("hidden");
            updateAiModels();
            aiResults.classList.add("hidden");
            aiResults.innerHTML = "";
        });
    }

    if(closeAiModal) {
        closeAiModal.addEventListener("click", () => {
            aiModal.classList.add("hidden");
        });
    }

    if(aiProvider) {
        aiProvider.addEventListener("change", updateAiModels);
    }

    if(btnRunAi) {
        btnRunAi.addEventListener("click", () => {
            if (!currentSessionId) {
                alert("No active session. Please load an analysis first.");
                return;
            }

            const provider = aiProvider.value;
            const model = provider === "microsoft" ? aiModelCustom.value : aiModel.value;
            const apiKey = aiApiKey.value.trim();
            const query = aiQuery.value.trim();
            const contextMode = document.querySelector('input[name="ai-context"]:checked').value;

            if (!apiKey) {
                alert("Please enter an API Key.");
                return;
            }
            if (provider === "microsoft" && !model.startsWith("http")) {
                alert("Please enter a valid Azure OpenAI endpoint URL for Microsoft Copilot.");
                return;
            }

            // Save key to local storage
            localStorage.setItem(`imm_ai_key_${provider}`, apiKey);

            btnRunAi.disabled = true;
            btnRunAi.innerHTML = '<box-icon name="loader-alt" animation="spin"></box-icon> Analyzing... (This may take a minute)';
            btnRunAi.innerHTML = '<box-icon name="loader-alt" animation="spin"></box-icon> Transmitting context to AI...';

            fetch("/api/ai/analyze", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    provider: provider,
                    model: model,
                    api_key: apiKey,
                    context_mode: contextMode,
                    query: query
                })
            })
            .then(res => {
                if (!res.ok) throw new Error("AI Request Failed");
                return res.json();
            })
            .then(data => {
                if (data.markdown_report) {
                    currentAiMarkdown = data.markdown_report;
                    aiReportContainer.innerHTML = marked.parse(data.markdown_report);
                    
                    // Close modal and switch workspace
                    aiModal.classList.add("hidden");
                    navAiReportLink.classList.remove("disabled", "hidden");
                    navAiReportLink.click();
                } else {
                    alert("Received empty response from AI.");
                }
            })
            .catch(err => {
                console.error("AI Error:", err);
                alert(`AI Analysis Error: ${err.message}`);
            })
            .finally(() => {
                btnRunAi.disabled = false;
                btnRunAi.innerHTML = '<box-icon name="bolt" type="solid" animation="flashing-hover"></box-icon> Run Deep Analysis';
            });
        });
    }
    if (btnAiDownloadMd) {
        btnAiDownloadMd.addEventListener("click", () => {
            if (!currentAiMarkdown) return;
            const blob = new Blob([currentAiMarkdown], { type: "text/markdown" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `APex_AI_Report_${currentSessionId || 'export'}.md`;
            a.click();
            URL.revokeObjectURL(url);
        });
    }

    if (btnAiDownloadPdf) {
        btnAiDownloadPdf.addEventListener("click", () => {
            window.print();
        });
    }

});
