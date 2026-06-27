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
    const resultsWorkspace = document.getElementById("results-workspace");
    const rulesWorkspace = document.getElementById("rules-workspace");
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
    const timelineContainer = document.getElementById("timeline-container");
    const reportContainer = document.getElementById("report-container");
    const rulesListContainer = document.getElementById("rules-list-container");
    const rulesCount = document.getElementById("rules-count");
    
    // Actions
    const btnBrowseFile = document.getElementById("btn-browse-file");
    const btnBrowseFolder = document.getElementById("btn-browse-folder");
    const btnDownloadPdf = document.getElementById("btn-download-pdf");
    const btnDownloadMd = document.getElementById("btn-download-md");
    const btnAnalyzeNew = document.getElementById("btn-analyze-new");

    // --- Init ---
    loadRulesDatabase();

    // --- Navigation ---
    navDashboardLink.addEventListener("click", (e) => {
        e.preventDefault();
        switchNavigation(navDashboardLink);
        rulesWorkspace.classList.add("hidden");
        if (currentSessionId) {
            uploadWorkspace.classList.add("hidden");
            resultsWorkspace.classList.remove("hidden");
        } else {
            resultsWorkspace.classList.add("hidden");
            uploadWorkspace.classList.remove("hidden");
        }
    });

    navRulesLink.addEventListener("click", (e) => {
        e.preventDefault();
        switchNavigation(navRulesLink);
        uploadWorkspace.classList.add("hidden");
        resultsWorkspace.classList.add("hidden");
        rulesWorkspace.classList.remove("hidden");
        loadRulesDatabase();
    });

    // Dummy scroll navigation handlers
    navTimelineLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (navTimelineLink.classList.contains("disabled")) return;
        document.getElementById("panel-timeline").scrollIntoView({ behavior: "smooth" });
    });

    navReportLink.addEventListener("click", (e) => {
        e.preventDefault();
        if (navReportLink.classList.contains("disabled")) return;
        document.getElementById("panel-report").scrollIntoView({ behavior: "smooth" });
    });

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

    logDropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        logDropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            // Drag and drop folders or files
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

    function handleFilesUpload(fileList) {
        // Show progress UI, hide upload details
        logDropzone.classList.add("hidden");
        uploadProgressContainer.classList.remove("hidden");
        updateProgress(10, "Uploading logs...", stepUpload);

        const formData = new FormData();
        
        // Append all selected files
        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            
            // Reconstruct directory paths if present (from folder pickers)
            // HTML5 provides webkitRelativePath for directory uploads
            const path = file.webkitRelativePath || file.name;
            formData.append("files", file, path);
        }

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
                
                // Extraction and analysis steps progress bar mapping
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
                                loadRulesDatabase(); // Refresh rules to show learned items
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

                renderReport(data.markdown_report);

                originalTimeline = data.timeline;
                renderTimeline(originalTimeline);

                uploadWorkspace.classList.add("hidden");
                rulesWorkspace.classList.add("hidden");
                resultsWorkspace.classList.remove("hidden");
                switchNavigation(navDashboardLink);

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

                    // Escape regex patterns for display
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
        return md;
    }

    function renderReport(markdownText) {
        const cleanMarkdown = preprocessMarkdown(markdownText);
        reportContainer.innerHTML = marked.parse(cleanMarkdown);
        
        try {
            mermaid.init(undefined, document.querySelectorAll(".mermaid"));
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

        if (filtered.length === 0) {
            timelineContainer.innerHTML = `<div class="text-center text-muted" style="padding: 40px 0;">No log entries match the selected filter.</div>`;
            return;
        }

        filtered.forEach((entry, idx) => {
            const node = document.createElement("div");
            node.className = `timeline-node ${entry.log_level}`;
            
            let icon = '<i class="fa-solid fa-info"></i>';
            if (entry.log_level === "CRITICAL" || (entry.log_level === "ERROR" && entry.metadata.is_crash)) {
                icon = '<i class="fa-solid fa-triangle-exclamation"></i>';
            } else if (entry.log_level === "ERROR") {
                icon = '<i class="fa-solid fa-circle-exclamation"></i>';
            } else if (entry.log_level === "WARNING") {
                icon = '<i class="fa-solid fa-shuffle"></i>';
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
                const contentDiv = node.querySelector(".timeline-content");
                let detailBlock = contentDiv.querySelector(".timeline-details");
                if (detailBlock) {
                    detailBlock.remove();
                } else {
                    detailBlock = document.createElement("div");
                    detailBlock.className = "timeline-details";
                    
                    let metaInfo = `Log Level: ${entry.log_level}\nSource File: ${entry.source_file}\n`;
                    if (entry.metadata.client_ip) metaInfo += `Client IP: ${entry.metadata.client_ip}\n`;
                    if (entry.metadata.status_code) metaInfo += `HTTP Code: ${entry.metadata.status_code}\n`;
                    if (entry.metadata.pattern_id) metaInfo += `Matched Rule ID: ${entry.metadata.pattern_id}\n`;
                    
                    detailBlock.innerHTML = `
                        <strong style="color:var(--accent-blue)">Metadata:</strong>
                        <pre style="margin:8px 0; color:#fff">${escapeHtml(metaInfo)}</pre>
                        <strong style="color:var(--accent-blue)">Raw Log Segment:</strong>
                        <pre style="white-space:pre-wrap; margin-top:8px; color:#fff">${escapeHtml(entry.message)}</pre>
                    `;
                    contentDiv.appendChild(detailBlock);
                }
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
        resultsWorkspace.classList.add("hidden");
        rulesWorkspace.classList.add("hidden");
        uploadWorkspace.classList.remove("hidden");
        switchNavigation(navDashboardLink);
        document.querySelectorAll(".nav-item").forEach(el => {
            if (el.id !== "nav-dashboard-link" && el.id !== "nav-rules-link") el.classList.add("disabled");
        });
    });
});
