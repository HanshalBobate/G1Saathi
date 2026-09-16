/**
 * G1Saathi — Modern Healthcare Client Application Controller
 * Handles Navigation, Real-time RAG Chat, File Dropzone, Indexing, and Telemetry
 */

(function () {
    "use strict";

    // ── Application State ──────────────────────────────────────────────────────
    const state = {
        activeTab: "ask",
        isIndexed: false,
        files: [],
        messages: [],
        isProcessing: false,
        status: null,
    };

    // ── DOM Elements ───────────────────────────────────────────────────────────
    const elements = {
        // Nav & Views
        navBtns: document.querySelectorAll(".nav-btn"),
        tabPanes: document.querySelectorAll(".tab-pane"),
        currentViewTitle: document.getElementById("current-view-title"),
        sidebar: document.getElementById("sidebar"),
        sidebarToggle: document.getElementById("sidebar-toggle"),

        // Badges & Meta
        providerBadge: document.getElementById("provider-badge"),
        modelNameDisplay: document.getElementById("model-name-display"),
        indexStatusBadge: document.getElementById("index-status-badge"),
        indexFilesCount: document.getElementById("index-files-count"),
        reportsCountBadge: document.getElementById("reports-count-badge"),

        // Chat View
        messagesContainer: document.getElementById("messages-container"),
        emptyState: document.getElementById("empty-state"),
        chatInput: document.getElementById("chat-input"),
        btnSend: document.getElementById("btn-send"),
        btnClearChat: document.getElementById("btn-clear-chat"),
        promptChips: document.querySelectorAll(".prompt-chip"),

        // Reports View
        pdfDropzone: document.getElementById("pdf-dropzone"),
        fileInput: document.getElementById("file-input"),
        btnBrowseFiles: document.getElementById("btn-browse-files"),
        btnLoadSamplesCard: document.getElementById("btn-load-samples-card"),
        btnQuickSamples: document.getElementById("btn-quick-samples"),
        fileQueueList: document.getElementById("file-queue-list"),
        queueCountBadge: document.getElementById("queue-count-badge"),
        btnStartIndex: document.getElementById("btn-start-index"),
        indexProgressBox: document.getElementById("index-progress-box"),
        progressSpinner: document.getElementById("progress-spinner"),
        progressStaticIcon: document.getElementById("progress-static-icon"),
        progressDetails: document.getElementById("progress-details"),
        btnClearQueue: document.getElementById("btn-clear-queue"),

        // Sources View
        statVectorStore: document.getElementById("stat-vectorstore"),
        statStoreStatus: document.getElementById("stat-store-status"),
        statEmbedModel: document.getElementById("stat-embed-model"),
        statEmbedProvider: document.getElementById("stat-embed-provider"),
        statDocCount: document.getElementById("stat-doc-count"),
        statChunksCount: document.getElementById("stat-chunks-count"),
        indexedDocsTbody: document.getElementById("indexed-docs-tbody"),
        btnClearIndex: document.getElementById("btn-clear-index"),

        // System View
        sysAppName: document.getElementById("sys-app-name"),
        sysPythonVer: document.getElementById("sys-python-ver"),
        sysProvider: document.getElementById("sys-provider"),
        sysChatModel: document.getElementById("sys-chat-model"),
        sysEmbedModel: document.getElementById("sys-embed-model"),
        sysPersistDir: document.getElementById("sys-persist-dir"),
        sysLogDir: document.getElementById("sys-log-dir"),
        sysLogSize: document.getElementById("sys-log-size"),

        // Modal & Toast
        sourceModal: document.getElementById("source-modal"),
        modalSourceTitle: document.getElementById("modal-source-title"),
        modalSourceBody: document.getElementById("modal-source-body"),
        modalCloseBtn: document.getElementById("modal-close-btn"),
        toastContainer: document.getElementById("toast-container"),
    };

    // ── Initialization ─────────────────────────────────────────────────────────
    document.addEventListener("DOMContentLoaded", () => {
        setupEventListeners();
        fetchStatus();
        fetchSystem();
        loadChatHistory();
    });

    function loadChatHistory() {
        try {
            const saved = localStorage.getItem("g1saathi_chat_history");
            if (saved) {
                const history = JSON.parse(saved);
                if (history && history.length > 0) {
                    if (elements.emptyState) elements.emptyState.style.display = "none";
                    state.messages = history;
                    history.forEach(msg => appendMessage(msg, true));
                }
            }
        } catch (e) {
            console.error("Failed to load chat history:", e);
        }
    }

    // ── Event Listeners ────────────────────────────────────────────────────────
    function setupEventListeners() {
        // Navigation Tabs
        elements.navBtns.forEach((btn) => {
            btn.addEventListener("click", () => {
                const targetTab = btn.getAttribute("data-tab");
                switchTab(targetTab);
            });
        });

        // 3D Plot Refresh
        const btnRefreshPlot = document.getElementById("btn-refresh-plot");
        if (btnRefreshPlot) {
            btnRefreshPlot.addEventListener("click", fetchAndRender3DPlot);
        }

        // Mobile Sidebar Toggle
        if (elements.sidebarToggle) {
            elements.sidebarToggle.addEventListener("click", () => {
                elements.sidebar.classList.toggle("open");
            });
        }

        // Chat Input handling
        elements.chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submitChat();
            }
        });

        elements.chatInput.addEventListener("input", autoResizeTextarea);
        elements.btnSend.addEventListener("click", submitChat);
        elements.btnClearChat.addEventListener("click", clearConversation);

        // Quick prompts
        elements.promptChips.forEach((chip) => {
            chip.addEventListener("click", () => {
                const prompt = chip.getAttribute("data-prompt");
                if (prompt) {
                    elements.chatInput.value = prompt;
                    submitChat();
                }
            });
        });

        // Dropzone & File Uploads
        elements.btnBrowseFiles.addEventListener("click", (e) => {
            e.stopPropagation();
            elements.fileInput.click();
        });

        elements.pdfDropzone.addEventListener("click", () => {
            elements.fileInput.click();
        });

        elements.fileInput.addEventListener("change", handleFileInputChange);

        ["dragenter", "dragover"].forEach((eventName) => {
            elements.pdfDropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                elements.pdfDropzone.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach((eventName) => {
            elements.pdfDropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                elements.pdfDropzone.classList.remove("dragover");
            });
        });

        elements.pdfDropzone.addEventListener("drop", handleFileDrop);

        // Load Sample Papers
        if (elements.btnLoadSamplesCard) {
            elements.btnLoadSamplesCard.addEventListener("click", loadSampleReports);
        }
        if (elements.btnQuickSamples) {
            elements.btnQuickSamples.addEventListener("click", loadSampleReports);
        }

        // Start Indexing
        elements.btnStartIndex.addEventListener("click", runIndexing);

        // Clear Queue
        if (elements.btnClearQueue) {
            elements.btnClearQueue.addEventListener("click", clearEntireQueue);
        }

        // Clear Index
        if (elements.btnClearIndex) {
            elements.btnClearIndex.addEventListener("click", clearIndex);
        }

        // Modal Close
        if (elements.modalCloseBtn) {
            elements.modalCloseBtn.addEventListener("click", closeModal);
        }
        window.addEventListener("click", (e) => {
            if (e.target === elements.sourceModal) {
                closeModal();
            }
        });

        // Retrieval Inspector
        const inspectorToggle = document.getElementById("inspector-toggle");
        if (inspectorToggle) {
            inspectorToggle.addEventListener("click", () => {
                const content = document.getElementById("inspector-content");
                const icon = document.getElementById("inspector-icon");
                if (content.style.display === "none") {
                    content.style.display = "block";
                    icon.textContent = "▲";
                } else {
                    content.style.display = "none";
                    icon.textContent = "▼";
                }
            });
        }

        // Phase 6: Deterministic Analysis
        const btnAnalyze = document.getElementById("btn-analyze-report");
        const btnCompare = document.getElementById("btn-compare-reports");
        if (btnAnalyze) btnAnalyze.addEventListener("click", handleAnalyzeSingle);
        if (btnCompare) btnCompare.addEventListener("click", handleCompareTrends);

        // Phase 8: Evaluation Center
        const btnRunEval = document.getElementById("btn-run-eval");
        const btnExportEval = document.getElementById("btn-export-eval");
        const btnDemoMode = document.getElementById("btn-demo-mode");
        if (btnRunEval) btnRunEval.addEventListener("click", runEvaluation);
        if (btnExportEval) btnExportEval.addEventListener("click", () => window.location.href = "/api/evaluation/export/csv");
        if (btnDemoMode) btnDemoMode.addEventListener("click", enterDemoMode);
    }

    // ── Phase 6: Deterministic Report Analysis ────────────────────────────────
    async function handleAnalyzeSingle() {
        if (state.files.length === 0) {
            showToast("No files in the queue to analyze. Please upload a PDF first.", "error");
            return;
        }
        
        // Pick the first file in the queue for demonstration
        const filename = state.files[0].name;
        const container = document.getElementById("analysis-results-container");
        container.style.display = "block";
        container.innerHTML = `<div class="progress-spinner" style="display:inline-block; vertical-align:middle; margin-right:8px;"></div> Analyzing ${escapeHtml(filename)} deterministically...`;
        
        try {
            const res = await fetch("/api/analyze-report", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename })
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error);
            
            if (!data.measurements || data.measurements.length === 0) {
                container.innerHTML = `<div style="color:var(--text-muted)">No biomarkers identified in <b>${escapeHtml(filename)}</b> using deterministic extraction.</div>`;
                return;
            }
            
            let html = `<h4>Extracting from: ${escapeHtml(data.document)}</h4>`;
            html += `<table class="data-table mt-2">
                <thead><tr><th>Biomarker</th><th>Value</th><th>Range</th><th>Status</th><th>Confidence</th></tr></thead><tbody>`;
                
            data.measurements.forEach(m => {
                let badgeClass = "badge-gray";
                if (m.classification === "HIGH") badgeClass = "badge-amber";
                if (m.classification === "LOW") badgeClass = "badge-blue";
                if (m.classification === "NORMAL") badgeClass = "badge-green";
                
                const rangeStr = (m.ref_low !== null && m.ref_high !== null) ? `${m.ref_low} - ${m.ref_high}` : 
                                 (m.ref_high !== null) ? `< ${m.ref_high}` : 
                                 (m.ref_low !== null) ? `> ${m.ref_low}` : "N/A";
                                 
                html += `<tr>
                    <td><strong>${escapeHtml(m.biomarker)}</strong></td>
                    <td>${m.value} ${escapeHtml(m.unit || "")}</td>
                    <td style="font-size:0.85em; color:var(--text-muted)">${rangeStr}</td>
                    <td><span class="badge ${badgeClass}">${m.classification}</span></td>
                    <td><small>${(m.extraction_confidence * 100).toFixed(0)}%</small></td>
                </tr>`;
            });
            
            html += `</tbody></table>`;
            container.innerHTML = html;
            
        } catch (err) {
            container.innerHTML = `<div style="color:var(--accent-danger)">Analysis failed: ${escapeHtml(err.message)}</div>`;
        }
    }

    async function handleCompareTrends() {
        if (state.files.length < 2) {
            showToast("Please upload at least 2 PDF reports (e.g. August and September CBC) to compare trends.", "error");
            return;
        }
        
        // We will just compare the first two files in the queue
        const f1 = state.files[0].name;
        const f2 = state.files[1].name;
        const container = document.getElementById("analysis-results-container");
        container.style.display = "block";
        container.innerHTML = `<div class="progress-spinner" style="display:inline-block; vertical-align:middle; margin-right:8px;"></div> Comparing ${escapeHtml(f1)} with ${escapeHtml(f2)}...`;
        
        try {
            const res = await fetch("/api/compare-reports", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filenames: [f1, f2] })
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error);
            
            if (!data.trends || data.trends.length === 0) {
                container.innerHTML = `<div style="color:var(--text-muted)">No overlapping biomarkers found between <b>${escapeHtml(f1)}</b> and <b>${escapeHtml(f2)}</b> to compute trends.</div>`;
                return;
            }
            
            let html = `<h4>Longitudinal Comparison</h4>
                <p style="font-size:0.85em; color:var(--text-muted)">Older: ${escapeHtml(f1)} | Newer: ${escapeHtml(f2)}</p>
                <table class="data-table mt-2">
                <thead><tr><th>Biomarker</th><th>Previous</th><th>Latest</th><th>Change</th></tr></thead><tbody>`;
                
            data.trends.forEach(t => {
                let diffColor = t.change > 0 ? "var(--accent-danger)" : (t.change < 0 ? "var(--accent-info)" : "var(--text-muted)");
                let diffPrefix = t.change > 0 ? "↑ +" : (t.change < 0 ? "↓ " : "");
                
                html += `<tr>
                    <td><strong>${escapeHtml(t.biomarker)}</strong></td>
                    <td>${t.previous} ${escapeHtml(t.unit || "")}</td>
                    <td>${t.latest} ${escapeHtml(t.unit || "")}</td>
                    <td style="color:${diffColor}; font-weight:bold;">${diffPrefix}${t.change} ${escapeHtml(t.unit || "")}</td>
                </tr>`;
            });
            
            html += `</tbody></table>`;
            container.innerHTML = html;
            
        } catch (err) {
            container.innerHTML = `<div style="color:var(--accent-danger)">Comparison failed: ${escapeHtml(err.message)}</div>`;
        }
    }

    // ── Navigation Controller ──────────────────────────────────────────────────
    function switchTab(tabId) {
        state.activeTab = tabId;

        // Update nav buttons
        elements.navBtns.forEach((b) => {
            b.classList.toggle("active", b.getAttribute("data-tab") === tabId);
        });

        // Update panes
        elements.tabPanes.forEach((pane) => {
            pane.classList.toggle("active", pane.id === `tab-${tabId}`);
        });

        // Update title
        const titles = {
            ask: "Ask G1Saathi",
            reports: "Medical Reports & Ingestion",
            sources: "Knowledge Sources & Chroma DB",
            knowledge: "Medical Knowledge Explorer",
            evaluation: "Evaluation & Reliability Center",
            system: "System Diagnostics",
        };
        elements.currentViewTitle.textContent = titles[tabId] || "G1Saathi";

        // Close mobile sidebar if open
        elements.sidebar.classList.remove("open");

        if (tabId === "sources" || tabId === "system" || tabId === "evaluation") {
            fetchStatus();
            fetchSystem();
        }
        
        if (tabId === "evaluation") {
            fetchEvaluationResults();
        }
        
        if (tabId === "sources") {
            fetchAndRender3DPlot();
        }
        
        if (tabId === "knowledge") {
            fetchAndRenderOntology();
        }
    }

    // ── API: Status & State Sync ───────────────────────────────────────────────
    async function fetchStatus() {
        try {
            const res = await fetch("/api/status");
            if (!res.ok) throw new Error("Failed to fetch status");
            const data = await res.json();
            state.status = data;
            state.isIndexed = data.is_indexed;
            state.files = data.files || [];

            renderStatus(data);
        } catch (err) {
            console.error("Error fetching status:", err);
            showToast("Failed to reach G1Saathi backend.", "error");
        }
    }

    function renderStatus(data) {
        // Badges
        elements.providerBadge.textContent = data.provider.toUpperCase();
        elements.modelNameDisplay.textContent = `${data.chat_model} / ${data.embed_model}`;
        elements.reportsCountBadge.textContent = data.indexed_count !== undefined ? data.indexed_count : data.file_count;
        elements.queueCountBadge.textContent = `${data.file_count} files in queue`;

        const isIndexed = Boolean(data.is_indexed && (data.indexed_count > 0 || data.total_chunks > 0));
        if (isIndexed) {
            elements.indexStatusBadge.textContent = "ACTIVE";
            elements.indexStatusBadge.className = "badge badge-green";
            elements.indexFilesCount.textContent = `${data.indexed_count} report(s) (${data.total_chunks} chunks) indexed`;
        } else {
            elements.indexStatusBadge.textContent = "EMPTY";
            elements.indexStatusBadge.className = "badge badge-amber";
            elements.indexFilesCount.textContent = "No reports indexed";
        }

        // Enable index button if files exist in queue
        elements.btnStartIndex.disabled = data.file_count === 0 || state.isProcessing;

        // Render queue & table
        renderFileQueue(data.files);
        renderSourcesView(data);
    }

    function renderFileQueue(files) {
        if (!files || files.length === 0) {
            elements.fileQueueList.innerHTML = `<div class="empty-list-placeholder">No PDF reports in queue. Drop files on the left or load samples.</div>`;
            return;
        }

        elements.fileQueueList.innerHTML = files
            .map(
                (f) => `
            <div class="file-queue-item" id="queue-item-${escapeHtml(f.name)}">
                <div class="file-queue-left">
                    <span class="file-queue-icon">📄</span>
                    <div>
                        <div class="file-queue-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</div>
                        <div class="file-queue-size">${f.size_kb} KB</div>
                    </div>
                </div>
                <div class="file-queue-right">
                    <span class="badge token-badge" title="Cryptic Content Token: ${escapeHtml(f.token || 'N/A')}">
                        🔐 ${f.token ? escapeHtml(f.token.slice(0, 15)) + '...' : 'Processing'}
                    </span>
                    <button class="btn-remove-queue" data-filename="${escapeHtml(f.name)}" title="Remove this report from queue">&times;</button>
                </div>
            </div>
        `
            )
            .join("");

        // Attach delete listeners to remove buttons
        elements.fileQueueList.querySelectorAll(".btn-remove-queue").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const filename = btn.getAttribute("data-filename");
                deleteFileFromQueue(filename);
            });
        });
    }

    function renderSourcesView(data) {
        if (!elements.statVectorStore) return;

        const isIndexed = Boolean(data.is_indexed && (data.indexed_count > 0 || data.total_chunks > 0));
        elements.statStoreStatus.textContent = isIndexed ? "ACTIVE" : "EMPTY";
        elements.statStoreStatus.className = `stat-badge ${isIndexed ? "badge-green" : "badge-amber"}`;
        elements.statEmbedModel.textContent = data.embed_model;
        elements.statEmbedProvider.textContent = data.provider.toUpperCase();
        elements.statDocCount.textContent = data.indexed_count !== undefined ? data.indexed_count : 0;
        
        const statLastIndexed = document.getElementById("stat-last-indexed");
        if (statLastIndexed) {
            statLastIndexed.textContent = data.last_indexed || "N/A";
        }

        if (elements.statChunksCount) {
            elements.statChunksCount.textContent = `${data.total_chunks || 0} Chunks`;
        }

        const indexedDocs = data.indexed_documents || [];
        if (indexedDocs.length === 0) {
            elements.indexedDocsTbody.innerHTML = `<tr><td colspan="3" class="table-empty">No indexed documents found in Knowledge Base.</td></tr>`;
        } else {
            elements.indexedDocsTbody.innerHTML = indexedDocs
                .map(
                    (doc) => `
                <tr>
                    <td><strong>📄 ${escapeHtml(doc.name)}</strong></td>
                    <td><span class="badge badge-blue">${doc.chunks} chunk(s)</span> &bull; <span class="badge badge-gray">${doc.page_count} page(s)</span></td>
                    <td><span class="badge badge-green">✓ Indexed</span></td>
                </tr>
            `
                )
                .join("");
        }
    }

    async function fetchAndRender3DPlot() {
        const plotContainer = document.getElementById("vector-3d-plot");
        const placeholder = document.getElementById("plot-placeholder");
        
        if (!plotContainer) return;
        
        if (placeholder) {
            placeholder.textContent = "Loading 3D vector space...";
            placeholder.style.display = "block";
        }
        
        try {
            const res = await fetch("/api/embeddings/3d");
            const data = await res.json();
            
            if (!res.ok) {
                if (placeholder) {
                    placeholder.textContent = data.error || "Failed to load 3D plot.";
                }
                return;
            }
            
            if (placeholder) placeholder.style.display = "none";
            
            // Group points by source document for coloring
            const sources = {};
            data.points.forEach(pt => {
                if (!sources[pt.source]) {
                    sources[pt.source] = { x: [], y: [], z: [], text: [], page: [], token: pt.token };
                }
                sources[pt.source].x.push(pt.x);
                sources[pt.source].y.push(pt.y);
                sources[pt.source].z.push(pt.z);
                sources[pt.source].text.push(`<b>${pt.source}</b> (Page ${pt.page})<br>${pt.text}`);
                sources[pt.source].page.push(pt.page);
            });
            
            const traces = Object.keys(sources).map(sourceName => ({
                x: sources[sourceName].x,
                y: sources[sourceName].y,
                z: sources[sourceName].z,
                text: sources[sourceName].text,
                mode: 'markers',
                type: 'scatter3d',
                name: sourceName,
                marker: { 
                    size: 5, 
                    opacity: 0.8,
                    color: tokenToRGB(sources[sourceName].token)
                },
                hoverinfo: 'text'
            }));
            
            const layout = {
                margin: { l: 0, r: 0, b: 0, t: 0 },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { color: '#9ca3af' },
                scene: {
                    xaxis: { showbackground: false, gridcolor: '#374151', zerolinecolor: '#4b5563' },
                    yaxis: { showbackground: false, gridcolor: '#374151', zerolinecolor: '#4b5563' },
                    zaxis: { showbackground: false, gridcolor: '#374151', zerolinecolor: '#4b5563' }
                },
                legend: { x: 0, y: 1 }
            };
            
            Plotly.newPlot("vector-3d-plot", traces, layout, { responsive: true, displayModeBar: false });
            
        } catch (err) {
            console.error("Error loading 3D plot:", err);
            if (placeholder) {
                placeholder.textContent = "Error rendering plot. Is scikit-learn installed?";
                placeholder.style.display = "block";
            }
        }
    }

    async function fetchSystem() {
        try {
            const res = await fetch("/api/system");
            if (res.ok) {
                const sys = await res.json();
                elements.sysAppName.textContent = `${sys.app_name} v${sys.app_version}`;
                elements.sysPythonVer.textContent = sys.python_version;
                elements.sysProvider.textContent = sys.provider.toUpperCase();
                elements.sysChatModel.textContent = sys.chat_model;
                elements.sysEmbedModel.textContent = sys.embed_model;
                elements.sysPersistDir.textContent = sys.persist_dir;
                elements.sysLogDir.textContent = sys.log_dir;
                elements.sysLogSize.textContent = `${sys.log_file_size_kb} KB`;
            }

            const metricsRes = await fetch("/api/workflow/metrics");
            if (metricsRes.ok) {
                const metrics = await metricsRes.json();
                document.getElementById("metric-queries").textContent = metrics.queries;
                document.getElementById("metric-avg-llm").textContent = metrics.avg_llm_calls;
                document.getElementById("metric-avg-vector").textContent = metrics.avg_vector_searches;
                document.getElementById("metric-ext-search").textContent = metrics.external_research_queries;
                document.getElementById("metric-emergency").textContent = metrics.emergency_interceptions;
                document.getElementById("metric-insufficient").textContent = metrics.insufficient_evidence_responses;
                document.getElementById("metric-revisions").textContent = metrics.grounding_revisions;
            }
        } catch (err) {
            console.error("Failed to fetch system info/metrics:", err);
        }
    }

    // ── Phase 8: Evaluation Center ─────────────────────────────────────────────
    async function fetchEvaluationResults() {
        try {
            const res = await fetch("/api/evaluation/results");
            if (!res.ok) {
                // If it's a 404, it means results/latest.json doesn't exist yet, which is fine
                if (res.status === 404) {
                    renderEmptyEvaluation();
                } else {
                    throw new Error("Failed to fetch evaluation results");
                }
                return;
            }
            const data = await res.json();
            renderEvaluationUI(data);
        } catch (err) {
            console.error("Failed to load evaluation results:", err);
            renderEmptyEvaluation();
        }
    }

    function renderEmptyEvaluation() {
        document.getElementById("eval-total").textContent = "-";
        document.getElementById("eval-passed").textContent = "-";
        document.getElementById("eval-failed").textContent = "-";
        document.getElementById("eval-timestamp").textContent = "Never run";
        
        document.getElementById("eval-coverage").textContent = "-";
        document.getElementById("eval-claims").textContent = "-";
        document.getElementById("eval-emergencies").textContent = "-";
        document.getElementById("eval-external").textContent = "-";
        
        const tbody = document.querySelector("#eval-cases-table tbody");
        tbody.innerHTML = `<tr><td colspan="5" class="table-empty">No results found. Run evaluation suite.</td></tr>`;
    }

    function renderEvaluationUI(data) {
        document.getElementById("eval-total").textContent = data.summary.total_tests;
        document.getElementById("eval-passed").textContent = data.summary.passed_tests;
        document.getElementById("eval-failed").textContent = data.summary.failed_tests;
        document.getElementById("eval-timestamp").textContent = new Date(data.timestamp).toLocaleString();
        
        const avgCov = (data.summary.avg_evidence_coverage * 100).toFixed(1) + "%";
        document.getElementById("eval-coverage").textContent = avgCov;
        document.getElementById("eval-claims").textContent = data.summary.avg_claims_supported.toFixed(1);
        document.getElementById("eval-emergencies").textContent = data.summary.emergency_interceptions;
        document.getElementById("eval-external").textContent = data.summary.external_research_invocations;
        
        const tbody = document.querySelector("#eval-cases-table tbody");
        if (data.results.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="table-empty">No results found.</td></tr>`;
            return;
        }
        
        tbody.innerHTML = data.results.map(r => {
            const statusBadge = r.passed 
                ? `<span class="badge badge-green">PASS</span>` 
                : `<span class="badge badge-red">FAIL</span>`;
            
            return `
                <tr>
                    <td>${statusBadge}</td>
                    <td><span class="badge badge-gray">${r.category}</span></td>
                    <td title="${escapeHtml(r.query)}">${escapeHtml(r.query.length > 50 ? r.query.substring(0, 50) + '...' : r.query)}</td>
                    <td title="${escapeHtml(r.expected_behavior)}">${escapeHtml(r.expected_behavior.length > 50 ? r.expected_behavior.substring(0, 50) + '...' : r.expected_behavior)}</td>
                    <td><small>${escapeHtml(r.failure_reason || "Passed validation.")}</small></td>
                </tr>
            `;
        }).join("");
    }

    async function runEvaluation() {
        if (!confirm("This will execute the full evaluation suite, which can take several minutes. Ensure the vector DB is populated first. Continue?")) {
            return;
        }
        
        const btnRun = document.getElementById("btn-run-eval");
        const statusBox = document.getElementById("eval-status-box");
        
        btnRun.disabled = true;
        statusBox.style.display = "block";
        
        try {
            const res = await fetch("/api/evaluation/run", { method: "POST" });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error);
            
            showToast("Evaluation completed successfully.", "success");
            await fetchEvaluationResults();
            
        } catch (err) {
            showToast(`Evaluation failed: ${err.message}`, "error");
        } finally {
            btnRun.disabled = false;
            statusBox.style.display = "none";
        }
    }

    async function enterDemoMode() {
        
        // Let's implement demo mode logic
        // This simulates a full run being triggered with synthesized data if we want.
        // For now we just show a toast
        showToast("Hackathon Demo Mode Activated. Bypassing rate limits...", "success");
    }

    // ── Chat Controller ────────────────────────────────────────────────────────
    async function submitChat() {
        const query = elements.chatInput.value.trim();
        if (!query || state.isProcessing) return;

        // Hide empty state if first message
        if (elements.emptyState) {
            elements.emptyState.style.display = "none";
        }

        // Append User Message
        appendMessage({ role: "user", text: query });
        elements.chatInput.value = "";
        elements.chatInput.style.height = "auto";

        // Show Typing Indicator
        state.isProcessing = true;
        const typingId = showTypingIndicator();

        const contextMsgs = state.messages.slice(-6).map(m => ({
            role: m.role,
            text: m.text
        }));

        try {
            const res = await fetch("/api/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: query, context: contextMsgs }),
            });

            removeTypingIndicator(typingId);
            const data = await res.json();

            if (!res.ok) {
                appendMessage({
                    role: "assistant",
                    text: `⚠️ **Error:** ${data.error || "Failed to generate answer."}`,
                });
                return;
            }

            appendMessage({
                role: "assistant",
                text: data.answer,
                sources: data.sources || [],
                safetyAlert: data.safety_alert || null,
                agentTrace: data.agent_trace || [],
                evidenceMetrics: data.evidence_quality_metrics || null,
                taskPlan: data.task_plan || null,
                toolCalls: data.tool_calls || {},
                nextSteps: data.next_steps || [],
                informationGap: data.information_gap || null
            });

            // Populate Retrieval Inspector
            const inspector = document.getElementById("retrieval-inspector");
            const inspectorContent = document.getElementById("inspector-content");
            if (inspector && inspectorContent && data.retrieval_diagnostics) {
                inspector.style.display = "block";
                inspectorContent.innerHTML = `
                    <div style="margin-bottom: 4px;"><strong>Query:</strong> ${escapeHtml(query)}</div>
                    <div style="margin-bottom: 4px;"><strong>Retrieved chunks:</strong> ${data.retrieval_diagnostics.retrieval_count || 0}</div>
                    <div style="margin-bottom: 4px;"><strong>Average Score:</strong> ${data.retrieval_diagnostics.average_score || 'N/A'}</div>
                    <div style="margin-bottom: 4px;"><strong>Top Score:</strong> ${data.retrieval_diagnostics.top_score || 'N/A'}</div>
                    <div style="margin-bottom: 4px;"><strong>Sources count:</strong> ${data.retrieval_diagnostics.sources_count || 0}</div>
                    ${data.extracted_claims ? `
                        <div style="margin-top: 8px;"><strong>Extracted Claims:</strong></div>
                        <pre style="background:#f1f1f1; padding:8px; border-radius:4px; font-size:11px;">${escapeHtml(JSON.stringify(data.extracted_claims, null, 2))}</pre>
                    ` : ''}
                `;
            }

        } catch (err) {
            console.error("Error in submitChat:", err);
            removeTypingIndicator(typingId);
            appendMessage({
                role: "assistant",
                text: `⚠️ **Error:** ${err.message || "Could not reach the G1Saathi server."}`,
            });
        } finally {
            state.isProcessing = false;
        }
    }

    function appendMessage(msgObj, skipSave = false) {
        const { role, text, sources, safetyAlert, agentTrace, evidenceMetrics, taskPlan, toolCalls, nextSteps, informationGap } = msgObj;
        if (!skipSave) {
            state.messages.push(msgObj);
            localStorage.setItem("g1saathi_chat_history", JSON.stringify(state.messages));
        }

        const row = document.createElement("div");
        row.className = `message-row ${role}`;

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = role === "user" ? "👤" : "🩺";

        const bubble = document.createElement("div");
        bubble.className = "message-bubble";

        // 1. Safety emergency alert if flagged
        let alertText = null;
        if (typeof safetyAlert === "string" && safetyAlert.trim().length > 0) {
            alertText = safetyAlert;
        } else if (safetyAlert && typeof safetyAlert === "object" && safetyAlert.is_emergency && safetyAlert.safety_note) {
            alertText = safetyAlert.safety_note;
        }

        if (alertText) {
            const alertBox = document.createElement("div");
            alertBox.className = "safety-alert-box";
            alertBox.innerHTML = `
                <div class="safety-alert-icon">⚠️</div>
                <div class="safety-alert-content">
                    ${typeof marked !== "undefined" ? marked.parse(alertText) : escapeHtml(alertText)}
                </div>
            `;
            bubble.appendChild(alertBox);
        }

        // 2. Body Text (Markdown parse)
        const contentDiv = document.createElement("div");
        contentDiv.className = "message-text";
        if (typeof marked !== "undefined") {
            let formattedText = text.replace(/\[([^\]]+)\](?!\s*\()/g, (match, inner) => {
                return `<a class="citation-link">${match}</a>`;
            });
            contentDiv.innerHTML = marked.parse(formattedText);
        } else {
            contentDiv.textContent = text;
        }
        bubble.appendChild(contentDiv);

        // 3. Citations Accordion & Badges
        if (sources && sources.length > 0) {
            const hasExternal = sources.some(s => s.type === "external");
            const hasLocal = sources.some(s => s.type === "local" || !s.type);

            // Add Badge Header
            const badgeDiv = document.createElement("div");
            badgeDiv.className = "message-research-badge";
            badgeDiv.style.marginBottom = "8px";
            badgeDiv.style.fontSize = "0.75rem";
            badgeDiv.style.fontWeight = "600";
            if (hasExternal) {
                badgeDiv.innerHTML = `<span style="color: #3b82f6;">🌐 Live Research Used</span>`;
            } else {
                badgeDiv.innerHTML = `<span style="color: #10b981;">📚 Knowledge Base</span>`;
            }
            bubble.insertBefore(badgeDiv, contentDiv);

            const sourcesCard = document.createElement("div");
            sourcesCard.className = "sources-card";

            const toggleBtn = document.createElement("button");
            toggleBtn.className = "sources-toggle";
            toggleBtn.innerHTML = `<span>📑 Cited Sources (${sources.length})</span> <span>▼</span>`;

            const sourcesList = document.createElement("div");
            sourcesList.className = "sources-list";
            sourcesList.style.display = "none";

            // Local Sources
            const localSources = sources.filter(s => s.type === "local" || !s.type);
            if (localSources.length > 0) {
                const localHeader = document.createElement("div");
                localHeader.innerHTML = `<strong>📚 Local Knowledge</strong>`;
                localHeader.style.padding = "4px 8px";
                localHeader.style.fontSize = "0.8rem";
                sourcesList.appendChild(localHeader);

                localSources.forEach(src => {
                    const item = document.createElement("div");
                    item.className = "source-item";
                    item.innerHTML = `
                        <span class="source-file-badge">${escapeHtml(src.file || "Document")}</span>
                        <span class="source-page-badge">Page ${src.page || 1}</span>
                    `;
                    item.addEventListener("click", () => openSourceModal(src));
                    sourcesList.appendChild(item);
                });
            }

            // External Sources
            const extSources = sources.filter(s => s.type === "external");
            if (extSources.length > 0) {
                const extHeader = document.createElement("div");
                extHeader.innerHTML = `<strong style="margin-top: 8px; display: block;">🌐 External Research</strong>`;
                extHeader.style.padding = "4px 8px";
                extHeader.style.fontSize = "0.8rem";
                sourcesList.appendChild(extHeader);

                extSources.forEach(src => {
                    const item = document.createElement("a");
                    item.className = "source-item";
                    item.href = src.url;
                    item.target = "_blank";
                    item.style.textDecoration = "none";
                    item.innerHTML = `
                        <span class="source-file-badge" style="background: #2563eb;">${escapeHtml(src.domain || "Web")}</span>
                        <span class="source-page-badge" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px;">${escapeHtml(src.title)}</span>
                    `;
                    sourcesList.appendChild(item);
                });
            }

            toggleBtn.addEventListener("click", () => {
                const isHidden = sourcesList.style.display === "none";
                sourcesList.style.display = isHidden ? "flex" : "none";
                toggleBtn.querySelector("span:last-child").textContent = isHidden ? "▲" : "▼";
            });

            sourcesCard.appendChild(toggleBtn);
            sourcesCard.appendChild(sourcesList);
            bubble.appendChild(sourcesCard);
        }

        // 4. Agent Workflow Trace Accordion
        if (agentTrace && agentTrace.length > 0) {
            const traceCard = document.createElement("div");
            traceCard.className = "sources-card trace-card"; // Reuse styles from sources-card

            const toggleBtn = document.createElement("button");
            toggleBtn.className = "sources-toggle trace-toggle";
            toggleBtn.innerHTML = `<span>🔍 Agent Workflow</span> <span>▼</span>`;

            const traceList = document.createElement("div");
            traceList.className = "sources-list trace-list";
            traceList.style.display = "none";
            
            // Format trace steps
            let traceHtml = agentTrace.map(step => {
                const isErr = step.includes("✗");
                return `<div class="trace-item" style="color: ${isErr ? '#ef4444' : '#10b981'}; font-size: 0.9em; padding: 4px 8px;">${escapeHtml(step)}</div>`;
            }).join("");

            if (taskPlan) {
                traceHtml = `<div style="padding: 4px 8px; font-size: 0.85em; font-weight: bold; border-bottom: 1px solid var(--border-color); margin-bottom: 4px;">
                    Plan: ${taskPlan.task_type} -> [${taskPlan.steps.join(", ")}]
                </div>` + traceHtml;
            }
            if (toolCalls && Object.keys(toolCalls).length > 0) {
                traceHtml += `<div style="padding: 4px 8px; font-size: 0.8em; color: var(--text-muted); border-top: 1px solid var(--border-color); margin-top: 4px;">
                    Telemetry: ${Object.entries(toolCalls).map(([k,v]) => `${k}=${v}`).join(", ")}
                </div>`;
            }
            
            traceList.innerHTML = traceHtml;

            toggleBtn.addEventListener("click", () => {
                const isHidden = traceList.style.display === "none";
                traceList.style.display = isHidden ? "flex" : "none";
                toggleBtn.querySelector("span:last-child").textContent = isHidden ? "▲" : "▼";
            });

            traceCard.appendChild(toggleBtn);
            traceCard.appendChild(traceList);
            bubble.appendChild(traceCard);
        }

        // 4.5 Information Gap Alert
        if (informationGap && informationGap.status === "MISSING_INFORMATION") {
            const gapBox = document.createElement("div");
            gapBox.className = "safety-alert-box";
            gapBox.style.background = "rgba(245, 158, 11, 0.1)";
            gapBox.style.border = "1px solid #f59e0b";
            gapBox.innerHTML = `
                <div class="safety-alert-icon" style="color: #f59e0b;">❓</div>
                <div class="safety-alert-content" style="color: #b45309;">
                    <strong>Information Gap Detected:</strong> ${escapeHtml(informationGap.reason)}
                </div>
            `;
            bubble.appendChild(gapBox);
        }

        // 4.6 Next Steps
        if (nextSteps && nextSteps.length > 0) {
            const stepsCard = document.createElement("div");
            stepsCard.className = "sources-card trace-card";
            
            const stepsToggleBtn = document.createElement("button");
            stepsToggleBtn.className = "sources-toggle trace-toggle";
            stepsToggleBtn.innerHTML = `<span>💡 Suggested Next Steps</span> <span>▼</span>`;

            const stepsList = document.createElement("div");
            stepsList.className = "sources-list trace-list";
            stepsList.style.display = "none";
            stepsList.style.padding = "8px";
            
            stepsList.innerHTML = `<ul style="margin: 0; padding-left: 16px; font-size: 0.9em; color: var(--text-color);">` + 
                nextSteps.map(s => `<li style="margin-bottom: 4px;">${escapeHtml(s)}</li>`).join("") + 
                `</ul>`;

            stepsToggleBtn.addEventListener("click", () => {
                const isHidden = stepsList.style.display === "none";
                stepsList.style.display = isHidden ? "block" : "none";
                stepsToggleBtn.querySelector("span:last-child").textContent = isHidden ? "▲" : "▼";
            });

            stepsCard.appendChild(stepsToggleBtn);
            stepsCard.appendChild(stepsList);
            bubble.appendChild(stepsCard);
        }

        // 5. Evidence Quality Accordion
        if (evidenceMetrics && role === "assistant") {
            const metricsCard = document.createElement("div");
            metricsCard.className = "sources-card trace-card"; // Reuse styling
            
            const mToggleBtn = document.createElement("button");
            mToggleBtn.className = "sources-toggle trace-toggle";
            mToggleBtn.innerHTML = `<span>📊 Evidence Quality</span> <span>▼</span>`;

            const mList = document.createElement("div");
            mList.className = "sources-list trace-list";
            mList.style.display = "none";
            mList.style.padding = "10px";
            mList.style.fontSize = "0.9em";
            mList.style.lineHeight = "1.4";

            let statusColor = "#10b981"; // green
            let statusIcon = "✓";
            let statusText = evidenceMetrics.evidence_status;

            if (evidenceMetrics.evidence_status === "INSUFFICIENT") {
                statusColor = "#ef4444"; // red
                statusIcon = "⚠";
                statusText = "INSUFFICIENT<br><small style='color:#666;'>The available knowledge does not contain enough supporting information for a reliable answer.</small>";
            } else if (evidenceMetrics.evidence_status === "CONFLICTING") {
                statusColor = "#f59e0b"; // orange
                statusIcon = "⚠";
                statusText = "CONFLICTING<br><small style='color:#666;'>Relevant sources contain differing information.</small>";
            } else if (evidenceMetrics.evidence_status === "PARTIAL") {
                statusColor = "#f59e0b"; // orange
            }

            mList.innerHTML = `
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span>Evidence coverage</span> <strong>${evidenceMetrics.evidence_coverage}%</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span>Claims supported</span> <strong>${evidenceMetrics.claims_supported}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span>Sources used</span> <strong>${evidenceMetrics.sources_used}</strong>
                </div>
                <div style="border-top: 1px solid var(--border-color); padding-top: 8px; margin-top: 8px;">
                    <div style="color: #666; font-size: 0.8em; margin-bottom: 4px;">Status</div>
                    <div style="color: ${statusColor}; font-weight: bold;">
                        ${statusIcon} ${statusText}
                    </div>
                </div>
                <div style="margin-top: 10px; font-size: 0.75em; color: #888; background: var(--bg-1); padding: 6px; border-radius: 4px;">
                    ℹ️ Evidence coverage indicates how well the response is supported by retrieved sources. It is not a medical confidence score, diagnosis probability, or assessment of patient health.
                </div>
            `;

            mToggleBtn.addEventListener("click", () => {
                const isHidden = mList.style.display === "none";
                mList.style.display = isHidden ? "block" : "none";
                mToggleBtn.querySelector("span:last-child").textContent = isHidden ? "▲" : "▼";
            });

            metricsCard.appendChild(mToggleBtn);
            metricsCard.appendChild(mList);
            bubble.appendChild(metricsCard);
        }

        row.appendChild(avatar);
        row.appendChild(bubble);

        elements.messagesContainer.appendChild(row);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const id = `typing-${Date.now()}`;
        const row = document.createElement("div");
        row.className = "message-row assistant";
        row.id = id;

        row.innerHTML = `
            <div class="message-avatar">🩺</div>
            <div class="message-bubble typing-bubble">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        `;
        elements.messagesContainer.appendChild(row);
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function clearConversation() {
        state.messages = [];
        localStorage.removeItem("g1saathi_chat_history");
        elements.messagesContainer.innerHTML = "";
        if (elements.emptyState) {
            elements.messagesContainer.appendChild(elements.emptyState);
            elements.emptyState.style.display = "block";
        }
        showToast("Conversation cleared.", "info");
    }

    function autoResizeTextarea() {
        this.style.height = "auto";
        this.style.height = `${Math.min(this.scrollHeight, 140)}px`;
    }

    function scrollToBottom() {
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
    }

    // ── Uploads & Reports Management ───────────────────────────────────────────
    function handleFileInputChange(e) {
        const files = Array.from(e.target.files);
        if (files.length > 0) uploadFiles(files);
    }

    function handleFileDrop(e) {
        const files = Array.from(e.dataTransfer.files).filter((f) =>
            f.name.toLowerCase().endsWith(".pdf")
        );
        if (files.length > 0) {
            uploadFiles(files);
        } else {
            showToast("Please drop PDF documents only.", "error");
        }
    }

    async function uploadFiles(files) {
        const formData = new FormData();
        files.forEach((f) => formData.append("files", f));

        showToast(`Uploading ${files.length} document(s)...`, "info");
        state.isProcessing = true;
        elements.btnStartIndex.disabled = true;

        // Start round loading animation
        if (elements.progressSpinner) elements.progressSpinner.style.display = "block";
        if (elements.progressStaticIcon) elements.progressStaticIcon.style.display = "none";
        elements.indexProgressBox.style.display = "flex";
        elements.progressDetails.textContent = `Uploading ${files.length} report(s) to queue...`;

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData,
            });
            const data = await res.json();

            // Stop round loading animation immediately upon completion
            if (elements.progressSpinner) elements.progressSpinner.style.display = "none";

            if (!res.ok) {
                if (elements.progressStaticIcon) {
                    elements.progressStaticIcon.style.display = "inline-block";
                    elements.progressStaticIcon.textContent = "❌";
                }
                elements.progressDetails.textContent = `Upload failed: ${data.error || "Server error"}`;
                showToast(data.error || "Upload failed", "error");
                return;
            }

            if (elements.progressStaticIcon) {
                elements.progressStaticIcon.style.display = "inline-block";
                elements.progressStaticIcon.textContent = "✅";
            }

            if (data.saved && data.saved.length > 0) {
                showToast(`Uploaded ${data.saved.length} report(s) to queue!`, "success");
                elements.progressDetails.textContent = `Successfully uploaded ${data.saved.length} PDF(s) to queue!`;
            }

            // Report any rejected duplicates
            if (data.rejected && data.rejected.length > 0) {
                data.rejected.forEach((r) => {
                    showToast(`⚠️ ${r.name}: ${r.reason}`, "error");
                });
            }

            await fetchStatus();

            setTimeout(() => {
                if (!state.isProcessing && elements.indexProgressBox) {
                    elements.indexProgressBox.style.display = "none";
                }
            }, 3500);
        } catch (err) {
            if (elements.progressSpinner) elements.progressSpinner.style.display = "none";
            if (elements.progressStaticIcon) {
                elements.progressStaticIcon.style.display = "inline-block";
                elements.progressStaticIcon.textContent = "❌";
            }
            elements.progressDetails.textContent = `Upload network error: ${err.message}`;
            showToast("Upload network error.", "error");
        } finally {
            state.isProcessing = false;
            elements.btnStartIndex.disabled = false;
        }
    }

    async function deleteFileFromQueue(filename) {
        try {
            const res = await fetch("/api/delete-file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);

            showToast(`Removed '${filename}' from queue.`, "info");
            fetchStatus();
        } catch (err) {
            showToast(`Failed to remove file: ${err.message}`, "error");
        }
    }

    async function clearEntireQueue() {
        if (!confirm("Are you sure you want to remove all PDF reports from the queue?")) return;
        try {
            const res = await fetch("/api/clear-queue", { method: "POST" });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);

            showToast("Queue cleared successfully.", "info");
            fetchStatus();
        } catch (err) {
            showToast(`Failed to clear queue: ${err.message}`, "error");
        }
    }

    async function loadSampleReports() {
        showToast("Loading sample medical studies...", "info");
        try {
            const res = await fetch("/api/load-samples", { method: "POST" });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);

            showToast(data.message || "Loaded sample studies!", "success");
            fetchStatus();
        } catch (err) {
            showToast("Could not load sample reports.", "error");
        }
    }

    async function runIndexing() {
        state.isProcessing = true;
        elements.btnStartIndex.disabled = true;

        // Start round loading animation
        if (elements.progressSpinner) elements.progressSpinner.style.display = "block";
        if (elements.progressStaticIcon) elements.progressStaticIcon.style.display = "none";
        elements.indexProgressBox.style.display = "flex";
        elements.progressDetails.textContent = "Loading PDFs, chunking text, and building Chroma embeddings...";

        try {
            const res = await fetch("/api/index", { method: "POST" });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || "Ingestion failed");
            }

            // Stop the round loading animation immediately upon completion
            if (elements.progressSpinner) elements.progressSpinner.style.display = "none";
            if (elements.progressStaticIcon) {
                elements.progressStaticIcon.style.display = "inline-block";
                elements.progressStaticIcon.textContent = "✅";
            }

            const warnText = (data.scanned_files && data.scanned_files.length > 0)
                ? ` (⚠️ Scanned PDF warning: ${data.scanned_files.join(', ')})`
                : "";
            elements.progressDetails.textContent = `Index complete! ${data.num_chunks} chunks indexed into Chroma.${warnText}`;
            showToast("Documents successfully indexed into Chroma!", "success");

            await fetchStatus();

            // Auto-hide progress box after 4.5 seconds so it doesn't linger forever
            setTimeout(() => {
                if (!state.isProcessing && elements.indexProgressBox) {
                    elements.indexProgressBox.style.display = "none";
                }
            }, 4500);

        } catch (err) {
            // Stop round loading animation on error
            if (elements.progressSpinner) elements.progressSpinner.style.display = "none";
            if (elements.progressStaticIcon) {
                elements.progressStaticIcon.style.display = "inline-block";
                elements.progressStaticIcon.textContent = "❌";
            }
            elements.progressDetails.textContent = `Error: ${err.message}`;
            showToast(`Indexing error: ${err.message}`, "error");
        } finally {
            state.isProcessing = false;
            elements.btnStartIndex.disabled = false;
        }
    }

    async function clearIndex() {
        if (!confirm("Are you sure you want to clear the entire vector index and uploaded files?")) {
            return;
        }

        try {
            const res = await fetch("/api/clear", { method: "POST" });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);

            showToast("Vector store and uploads cleared.", "success");
            fetchStatus();
        } catch (err) {
            showToast(`Error clearing index: ${err.message}`, "error");
        }
    }

    // ── Source Citation Modal ──────────────────────────────────────────────────
    function openSourceModal(source) {
        elements.modalSourceTitle.textContent = `${source.file} (Page ${source.page})`;
        elements.modalSourceBody.textContent = source.snippet || "No preview snippet available.";
        elements.sourceModal.style.display = "flex";
    }

    function closeModal() {
        elements.sourceModal.style.display = "none";
    }

    // ── Toast Utility ──────────────────────────────────────────────────────────
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;

        const icon = type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️";
        toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;

        elements.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function tokenToRGB(token) {
        if (!token || token === "default") return "rgb(150, 150, 150)";
        let hash = 0;
        for (let i = 0; i < token.length; i++) {
            hash = token.charCodeAt(i) + ((hash << 5) - hash);
        }
        // Extract 3 distinct RGB channels, keeping them relatively bright (100-255)
        const r = (hash & 0xFF0000) >> 16;
        const g = (hash & 0x00FF00) >> 8;
        const b = hash & 0x0000FF;
        
        // Normalize to ensure visibility on dark mode
        const brightR = Math.max(100, Math.abs(r));
        const brightG = Math.max(100, Math.abs(g));
        const brightB = Math.max(100, Math.abs(b));
        
        return `rgb(${brightR}, ${brightG}, ${brightB})`;
    }

    // ── Knowledge Explorer ─────────────────────────────────────────────────────
    let ontologyNetwork = null;
    async function fetchAndRenderOntology() {
        const listContainer = document.getElementById("ontology-list");
        const graphContainer = document.getElementById("knowledge-graph-container");
        if (!listContainer || !graphContainer) return;
        
        try {
            const res = await fetch("/api/ontology");
            const data = await res.json();
            if (!res.ok) throw new Error(data.error);
            
            const entities = data.entities || [];
            renderOntologyList(entities);
            renderKnowledgeGraph(entities, graphContainer);
            
            // Search functionality
            const searchInput = document.getElementById("ontology-search");
            if (searchInput) {
                searchInput.addEventListener("input", (e) => {
                    const query = e.target.value.toLowerCase();
                    const filtered = entities.filter(ent => 
                        ent.canonical_name.toLowerCase().includes(query) || 
                        ent.aliases.some(a => a.toLowerCase().includes(query))
                    );
                    renderOntologyList(filtered);
                });
            }
            
            const refreshBtn = document.getElementById("btn-refresh-graph");
            if (refreshBtn) {
                refreshBtn.addEventListener("click", () => renderKnowledgeGraph(entities, graphContainer));
            }
            
        } catch (err) {
            console.error("Failed to load ontology:", err);
            listContainer.innerHTML = `<div style="color:var(--accent-danger)">Error loading ontology.</div>`;
        }
    }

    function renderOntologyList(entities) {
        const listContainer = document.getElementById("ontology-list");
        if (!listContainer) return;
        
        if (entities.length === 0) {
            listContainer.innerHTML = `<div style="color:var(--text-muted); padding:10px;">No terms found.</div>`;
            return;
        }
        
        listContainer.innerHTML = entities.map(ent => {
            const aliasesHtml = ent.aliases.map(a => {
                // simple language heuristic for styling badges
                let langClass = "lang-en";
                if (/[\u0900-\u097F]/.test(a)) { // Devanagari script (Hindi/Marathi)
                    langClass = "lang-hi";
                }
                return `<span class="ontology-badge ${langClass}">${escapeHtml(a)}</span>`;
            }).join("");
            
            const relatedHtml = ent.related_terms ? ent.related_terms.join(", ") : "None";
            
            return `
                <div class="ontology-item" onclick="highlightGraphNode('${escapeHtml(ent.canonical_name)}')">
                    <div class="ontology-canonical">${escapeHtml(ent.canonical_name)}</div>
                    <div class="ontology-badges">
                        <span class="ontology-badge category">${escapeHtml(ent.category)}</span>
                        ${aliasesHtml}
                    </div>
                    <div class="ontology-related">Related: ${escapeHtml(relatedHtml)}</div>
                </div>
            `;
        }).join("");
    }
    
    // Global scope so it can be called from onclick
    window.highlightGraphNode = function(nodeId) {
        if (ontologyNetwork) {
            ontologyNetwork.selectNodes([nodeId]);
            ontologyNetwork.focus(nodeId, { scale: 1.5, animation: true });
        }
    };

    function renderKnowledgeGraph(entities, container) {
        if (typeof vis === 'undefined') {
            container.innerHTML = `<div style="padding:20px;">Vis.js not loaded.</div>`;
            return;
        }
        
        const nodes = new vis.DataSet();
        const edges = new vis.DataSet();
        
        const addedNodes = new Set();
        
        // Colors by category
        const colors = {
            cardiovascular: { background: '#1e3a8a', border: '#3b82f6' },
            infectious: { background: '#064e3b', border: '#10b981' },
            respiratory: { background: '#701a75', border: '#d946ef' },
            symptom: { background: '#7f1d1d', border: '#ef4444' },
            metabolic: { background: '#78350f', border: '#f59e0b' },
            default: { background: '#1e293b', border: '#64748b' }
        };
        
        entities.forEach(ent => {
            const cat = ent.category || 'default';
            const nodeColor = colors[cat] || colors.default;
            
            if (!addedNodes.has(ent.canonical_name)) {
                nodes.add({
                    id: ent.canonical_name,
                    label: ent.canonical_name,
                    color: nodeColor,
                    shape: 'dot',
                    size: 20,
                    font: { color: '#f1f5f9', size: 14 }
                });
                addedNodes.add(ent.canonical_name);
            }
            
            // Add related terms as edges
            if (ent.related_terms) {
                ent.related_terms.forEach(rel => {
                    // add related node if it doesn't exist (make it smaller)
                    if (!addedNodes.has(rel)) {
                        nodes.add({
                            id: rel,
                            label: rel,
                            color: { background: '#334155', border: '#475569' },
                            shape: 'dot',
                            size: 10,
                            font: { color: '#94a3b8', size: 10 }
                        });
                        addedNodes.add(rel);
                    }
                    edges.add({
                        from: ent.canonical_name,
                        to: rel,
                        color: { color: 'rgba(255,255,255,0.1)' }
                    });
                });
            }
        });
        
        const data = { nodes: nodes, edges: edges };
        const options = {
            nodes: {
                borderWidth: 2,
                shadow: true
            },
            edges: {
                width: 1,
                smooth: { type: 'continuous' }
            },
            physics: {
                stabilization: false,
                barnesHut: {
                    gravitationalConstant: -2000,
                    springConstant: 0.04,
                    springLength: 95
                }
            },
            interaction: {
                hover: true,
                zoomView: true,
                dragView: true
            }
        };
        
        ontologyNetwork = new vis.Network(container, data, options);
    }
})();
