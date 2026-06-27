document.addEventListener("DOMContentLoaded", () => {
    // State Variables
    let currentSessionId = null;
    let originalTimeline = [];
    let activeFilter = "all";

    // DOM Elements
    const logDropzone = document.getElementById("log-dropzone");
    const fileInput = document.getElementById("file-input");
    const uploadWorkspace = document.getElementById("upload-workspace");
    const resultsWorkspace = document.getElementById("results-workspace");
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
    const navTimelineLink = document.getElementById("nav-timeline-link");
    const navReportLink = document.getElementById("nav-report-link");
    const timelineContainer = document.getElementById("timeline-container");
    const reportContainer = document.getElementById("report-container");
    
    // Actions
    const btnDownloadPdf = document.getElementById("btn-download-pdf");
    const btnDownloadMd = document.getElementById("btn-download-md");
    const btnAnalyzeNew = document.getElementById("btn-analyze-new");

    // --- Drag and Drop File Upload ---
    logDropzone.addEventListener("click", () => fileInput.click());

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
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    function handleFileUpload(file) {
        if (!file.name.endsWith(".zip")) {
            alert("Error: Only ZIP files are supported.");
            return;
        }

        // Show progress UI, hide upload details
        logDropzone.classList.add("hidden");
        uploadProgressContainer.classList.remove("hidden");
        updateProgress(10, "Uploading zip archive...", stepUpload);

        const formData = new FormData();
        formData.append("file", file);

        // API Upload Request with manual step simulation for extraction and parsing
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/upload", true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 40); // upload constitutes 40% of loading bar
                updateProgress(percent, `Uploading log archive (${percent}%)`, stepUpload);
            }
        };

        xhr.onload = function() {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                currentSessionId = response.session_id;
                
                // Simulate fast backend steps UI progress
                setTimeout(() => {
                    updateProgress(60, "Extracting log contents...", stepExtract);
                    setTimeout(() => {
                        updateProgress(80, "Parsing files & mapping streams...", stepParse);
                        setTimeout(() => {
                            updateProgress(100, "Correlating logs & generating report...", stepAnalyze);
                            setTimeout(() => {
                                // Transition to Results Dashboard
                                loadReportResults(currentSessionId);
                            }, 500);
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
            
            // Mark previous steps complete
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
    }

    // --- Load analysis report from backend ---
    function loadReportResults(sessionId) {
        fetch(`/api/report/${sessionId}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch report data");
                return res.json();
            })
            .then(data => {
                // Update navigation state
                document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("disabled"));
                
                // Update metrics counters
                metricCrashes.innerText = data.summary.crashes_count;
                metricFailovers.innerText = data.summary.failovers_count;
                metricErrors.innerText = data.summary.http_errors_count;
                metricEntries.innerText = data.timeline.length;

                // Adjust Metrics card colors dynamically
                if (data.summary.crashes_count > 0) {
                    metricCrashes.parentElement.parentElement.classList.add("critical");
                }

                // Render Report Markdown
                renderReport(data.markdown_report);

                // Populate Timeline
                originalTimeline = data.timeline;
                renderTimeline(originalTimeline);

                // Switch visible workspaces
                uploadWorkspace.classList.add("hidden");
                resultsWorkspace.classList.remove("hidden");

                // Scroll to top
                document.querySelector(".main-content").scrollTop = 0;
            })
            .catch(err => {
                console.error("Error loading results: ", err);
                alert("Error loading diagnostic results.");
                resetUploadUI();
            });
    }

    // --- Preprocess alert boxes & render Markdown ---
    function preprocessMarkdown(md) {
        // Formats GitHub blockquotes (> [!NOTE]) into inline alert classes
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
        
        // Render Mermaid Diagrams if present
        try {
            mermaid.init(undefined, document.querySelectorAll(".mermaid"));
        } catch (e) {
            console.error("Error initializing mermaid: ", e);
        }
    }

    // --- Render Chronological Timeline list ---
    function renderTimeline(entries) {
        timelineContainer.innerHTML = "";
        
        // Apply active filter
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
            
            // Set indicator icon
            let icon = '<i class="fa-solid fa-info"></i>';
            if (entry.log_level === "CRITICAL" || (entry.log_level === "ERROR" && entry.metadata.is_crash)) {
                icon = '<i class="fa-solid fa-triangle-exclamation"></i>';
            } else if (entry.log_level === "ERROR") {
                icon = '<i class="fa-solid fa-circle-exclamation"></i>';
            } else if (entry.log_level === "WARNING") {
                icon = '<i class="fa-solid fa-shuffle"></i>';
            }

            // Simple timestamp display
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
            
            // Expand details codeblock on click
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
        uploadWorkspace.classList.remove("hidden");
        document.querySelectorAll(".nav-item").forEach(el => {
            if (el.id !== "nav-dashboard-link") el.classList.add("disabled");
        });
    });
});
