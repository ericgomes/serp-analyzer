document.addEventListener("DOMContentLoaded", () => {
    // Parse current active query from URL parameter 'q'
    const urlParams = new URLSearchParams(window.location.search);
    let currentQuery = urlParams.get('q') || "Marcelo Baptista de Oliveira";
    
    // Set placeholder query input in the header
    const newQueryInput = document.getElementById("new-query-input");
    if (newQueryInput) {
        newQueryInput.value = currentQuery;
    }

    // Load multi-query analysis store from localStorage
    let store = {};
    const localStore = localStorage.getItem("reputation_analyses_store");
    if (localStore) {
        try {
            store = JSON.parse(localStore);
        } catch (e) {
            console.error("Erro ao carregar store de análises:", e);
        }
    }

    // Migration of legacy 'analysisResults' to 'reputation_analyses_store'
    const legacyResults = localStorage.getItem("analysisResults");
    if (legacyResults && Object.keys(store).length === 0) {
        try {
            const results = JSON.parse(legacyResults);
            const report = localStorage.getItem("consolidatedReport");
            const reportTime = localStorage.getItem("consolidatedReportTime");
            
            store["Marcelo Baptista de Oliveira"] = {
                results: results,
                report: report || (typeof consolidatedReport !== 'undefined' ? consolidatedReport : ""),
                reportTime: reportTime || (typeof consolidatedReportTime !== 'undefined' ? consolidatedReportTime : "")
            };
            localStorage.setItem("reputation_analyses_store", JSON.stringify(store));
        } catch (e) {
            console.error("Erro ao migrar dados legados:", e);
        }
    }

    // If store is still empty, initialize with default Marcelo Baptista de Oliveira using static JS files
    if (Object.keys(store).length === 0) {
        let results = [];
        if (typeof analysisResults !== 'undefined') {
            results = analysisResults;
        } else if (typeof searchResults !== 'undefined') {
            results = searchResults;
        }
        
        store["Marcelo Baptista de Oliveira"] = {
            results: results,
            report: typeof consolidatedReport !== 'undefined' ? consolidatedReport : "",
            reportTime: typeof consolidatedReportTime !== 'undefined' ? consolidatedReportTime : ""
        };
        localStorage.setItem("reputation_analyses_store", JSON.stringify(store));
    }

    // Handle Active query data selection
    let activeQueryData = store[currentQuery];
    if (!activeQueryData) {
        // If currentQuery not in store, initialize a blank structure
        activeQueryData = {
            results: [],
            report: "",
            reportTime: ""
        };
    }

    // Update global variables for page scope
    let analysisResultsList = activeQueryData.results || [];
    const isAiLoaded = analysisResultsList.length > 0;
    const data = isAiLoaded ? analysisResultsList : (typeof searchResults !== 'undefined' ? searchResults : []);

    // Populating dropdown and binding reload on change
    const querySelect = document.getElementById("query-select");
    if (querySelect) {
        querySelect.innerHTML = "";
        
        // Collect all keys
        const keys = Object.keys(store);
        if (!keys.includes(currentQuery)) {
            keys.push(currentQuery);
        }
        
        keys.forEach(k => {
            const opt = document.createElement("option");
            opt.value = k;
            opt.textContent = k;
            if (k === currentQuery) {
                opt.selected = true;
            }
            querySelect.appendChild(opt);
        });

        querySelect.addEventListener("change", (e) => {
            const val = e.target.value;
            window.location.search = `?q=${encodeURIComponent(val)}`;
        });
    }

    // Helper to determine if an entry represents a connection/scraping error or access limitation
    function isAccessError(item) {
        const cat = (item.categoria || "").toLowerCase();
        const theme = (item.tema || "").toLowerCase();
        const summary = (item.resumo || "").toLowerCase();
        
        if (cat.includes("erro") || theme.includes("erro") || 
            summary.includes("page.goto") || summary.includes("access denied") || 
            summary.includes("unable to retrieve content")) {
            return true;
        }
        
        if (cat.includes("mídia social") || cat.includes("redes sociais") || cat.includes("mídias sociais")) {
            if (summary.includes("bloqueado") || 
                summary.includes("não pôde ser analisada") || 
                summary.includes("não pôde ser analisado") || 
                summary.includes("restrições de login") || 
                summary.includes("sem a reprodução")) {
                return true;
            }
        }
        return false;
    }
    
    // Filter connection errors from Tabela de Resultados
    const errorFreeData = data.filter(item => !isAccessError(item));
    
    // Update subtitle count dynamically
    const subtitleCount = document.getElementById("subtitle-count");
    if (subtitleCount) {
        subtitleCount.textContent = errorFreeData.length;
    }
    
    // Pagination state
    let filteredData = [...errorFreeData];
    let currentPage = 1;
    const itemsPerPage = 10;
    
    
    // UI Elements
    const resultsContainer = document.getElementById("results-container");
    const searchBox = document.getElementById("search-box");
    const resultsCountText = document.getElementById("results-count");
    const viewModeIndicator = document.getElementById("view-mode-indicator");
    const paginationContainer = document.getElementById("pagination-container");
    
    // Errors Tab UI Elements
    const errorsContainer = document.getElementById("errors-container");
    const errorsCountText = document.getElementById("errors-count");
    
    // Tabs
    const tabsNavigation = document.getElementById("tabs-navigation");
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    const reportContainer = document.getElementById("report-container");
    
    // KPI Counters elements
    const kpiTotal = document.getElementById("kpi-total");
    const kpiDomains = document.getElementById("kpi-domains");
    const kpiSocial = document.getElementById("kpi-social");

    // Buttons
    const downloadPdfBtn = document.getElementById("download-pdf");
    const backToTopBtn = document.getElementById("back-to-top");

    // Theme Toggle Functionality
    const themeToggleBtn = document.getElementById("theme-toggle");
    if (themeToggleBtn) {
        const sunIcon = themeToggleBtn.querySelector(".sun-icon");
        const moonIcon = themeToggleBtn.querySelector(".moon-icon");
        const savedTheme = localStorage.getItem("theme") || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
        
        if (savedTheme === "light") {
            document.body.classList.add("light-theme");
            if (sunIcon) sunIcon.style.display = "none";
            if (moonIcon) moonIcon.style.display = "block";
        }
        
        themeToggleBtn.addEventListener("click", () => {
            const isLight = document.body.classList.toggle("light-theme");
            if (isLight) {
                localStorage.setItem("theme", "light");
                if (sunIcon) sunIcon.style.display = "none";
                if (moonIcon) moonIcon.style.display = "block";
            } else {
                localStorage.setItem("theme", "dark");
                if (sunIcon) sunIcon.style.display = "block";
                if (moonIcon) moonIcon.style.display = "none";
            }
        });
    }

    // Configure View Mode
    if (isAiLoaded) {
        tabsNavigation.style.display = "flex";
        const resultsSubtabs = document.getElementById("results-subtabs");
        if (resultsSubtabs) resultsSubtabs.style.display = "flex";
        viewModeIndicator.textContent = "Detalhamento e Análise de IA Ativos";
        viewModeIndicator.style.color = "var(--success)";
        
        // Setup Tab switching
        tabButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                const targetTab = btn.getAttribute("data-tab");
                
                tabButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                
                tabContents.forEach(content => {
                    if (content.id === targetTab) {
                        content.style.display = "block";
                    } else {
                        content.style.display = "none";
                    }
                });
            });
        });
        
        // Render consolidated report tab
        renderConsolidatedReport();
        // Render errors list
        renderErrorsList();
    }

    // Setup sub-tab switching inside the Results tab (Resultados / Erros de Conexão/Acesso)
    const subtabButtons = document.querySelectorAll(".subtab-btn");
    const subtabContents = document.querySelectorAll(".subtab-content");
    subtabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetSubtab = btn.getAttribute("data-subtab");

            subtabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            subtabContents.forEach(content => {
                const isActive = content.id === targetSubtab;
                content.classList.toggle("active", isActive);
                content.style.display = isActive ? "block" : "none";
            });
        });
    });

    // WebSocket Integration for real-time progressive search and analysis
    const startBtn = document.getElementById("start-analysis-btn");
    const clearBtn = document.getElementById("clear-cache-btn");
    const progressContainer = document.getElementById("progress-container");
    const progressStatusText = document.getElementById("progress-status-text");
    const progressPercentage = document.getElementById("progress-percentage");
    const progressBarFill = document.getElementById("progress-bar-fill");
    const logsContent = document.getElementById("logs-content");
    
    let ws;
    let localAnalysisResults = [...analysisResultsList];

    function appendLog(line) {
        if (!logsContent) return;
        const p = document.createElement("div");
        p.textContent = line;
        logsContent.appendChild(p);
        // Auto scroll console to bottom
        logsContent.scrollTop = logsContent.scrollHeight;
    }

    // Configure Backend Host (handling file:/// protocol fallback to local FastAPI server)
    let backendHost = window.location.host;
    if (!backendHost || window.location.protocol === "file:") {
        backendHost = "127.0.0.1:8090";
    }

    function initWebSocket() {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${wsProtocol}//${backendHost}/ws/progress`;
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log("WebSocket conectado.");
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === "log") {
                appendLog(data.message);
                updateUIState(data.state);
            } 
            else if (data.type === "state") {
                updateUIState(data.data);
                if (data.data.logs) {
                    logsContent.innerHTML = "";
                    data.data.logs.forEach(l => appendLog(l));
                }
            } 
            else if (data.type === "result") {
                const item = data.item;
                // Add or update results list
                const existingIdx = localAnalysisResults.findIndex(r => r.url === item.url);
                if (existingIdx >= 0) {
                    localAnalysisResults[existingIdx] = item;
                } else {
                    localAnalysisResults.push(item);
                }
                
                // Cache immediately in reputation_analyses_store
                store[currentQuery] = {
                    results: localAnalysisResults,
                    report: store[currentQuery]?.report || "",
                    reportTime: store[currentQuery]?.reportTime || ""
                };
                localStorage.setItem("reputation_analyses_store", JSON.stringify(store));
                
                // Refresh dashboard UI live
                refreshDashboardData(localAnalysisResults);
                updateUIState(data.state);
            }
            else if (data.type === "finished") {
                appendLog("🎉 Análise finalizada com sucesso!");
                const reportTime = new Date().toISOString().replace('T', ' ').substring(0, 19);
                
                // Cache final assets in reputation_analyses_store
                store[currentQuery] = {
                    results: data.results,
                    report: data.report,
                    reportTime: reportTime
                };
                localStorage.setItem("reputation_analyses_store", JSON.stringify(store));
                
                // Reload dashboard data
                localAnalysisResults = data.results;
                refreshDashboardData(localAnalysisResults);
                
                // Render consolidated report tab view
                activeQueryData = store[currentQuery];
                renderConsolidatedReport();
                
                if (progressContainer) progressContainer.style.display = "none";
                if (startBtn) startBtn.disabled = false;
                
                // Reload query selection dropdown options
                if (querySelect) {
                    const optExists = Array.from(querySelect.options).some(opt => opt.value === currentQuery);
                    if (!optExists) {
                        const opt = document.createElement("option");
                        opt.value = currentQuery;
                        opt.textContent = currentQuery;
                        opt.selected = true;
                        querySelect.appendChild(opt);
                    }
                }
            }
        };
        
        ws.onclose = () => {
            console.log("WebSocket desconectado. Tentando reconectar em 5 segundos...");
            setTimeout(initWebSocket, 5000);
        };
    }

    function updateUIState(state) {
        if (!state) return;
        
        if (state.is_running) {
            if (progressContainer) progressContainer.style.display = "block";
            if (startBtn) startBtn.disabled = true;
            
            const pct = state.total > 0 ? Math.round((state.progress / state.total) * 100) : 0;
            if (progressStatusText) progressStatusText.textContent = `Status: ${state.current_status}`;
            if (progressPercentage) progressPercentage.textContent = `${pct}%`;
            if (progressBarFill) progressBarFill.style.width = `${pct}%`;
        } else {
            if (progressContainer) progressContainer.style.display = "none";
            if (startBtn) startBtn.disabled = false;
        }
    }

    function refreshDashboardData(results) {
        // Apply active AI Mode configuration
        tabsNavigation.style.display = "flex";
        viewModeIndicator.textContent = "Detalhamento e Análise de IA Ativos";
        viewModeIndicator.style.color = "var(--success)";
        
        const cleanData = results.filter(item => !isAccessError(item));
        
        // Update variables in outer DOM scope
        filteredData = [...cleanData];
        if (subtitleCount) subtitleCount.textContent = cleanData.length;
        
        // Update KPIs and Tabela Results list view
        calculateKPIs(cleanData);
        updateResultsList();
        renderErrorsList();
    }

    const newAnalysisTriggerBtn = document.getElementById("new-analysis-trigger-btn");
    if (newAnalysisTriggerBtn) {
        newAnalysisTriggerBtn.addEventListener("click", () => {
            if (newQueryInput) {
                newQueryInput.value = "";
                newQueryInput.focus();
            }
            
            currentQuery = "";
            
            const cleanUrl = `${window.location.protocol}//${window.location.host}${window.location.pathname}`;
            window.history.pushState({ path: cleanUrl }, '', cleanUrl);
            
            if (querySelect) {
                let placeholderOpt = Array.from(querySelect.options).find(opt => opt.value === "");
                if (!placeholderOpt) {
                    placeholderOpt = document.createElement("option");
                    placeholderOpt.value = "";
                    placeholderOpt.textContent = "-- Iniciar Nova Análise --";
                    querySelect.insertBefore(placeholderOpt, querySelect.firstChild);
                }
                querySelect.value = "";
            }
            
            localAnalysisResults = [];
            activeQueryData = { results: [], report: "", reportTime: "" };
            refreshDashboardData([]);
            renderConsolidatedReport();
            appendLog("[Console] Pronto para criar uma nova análise. Digite o termo acima e clique em Analisar.");
        });
    }

    if (startBtn) {
        startBtn.addEventListener("click", () => {
            const newQueryVal = document.getElementById("new-query-input")?.value.trim() || "";
            if (!newQueryVal) {
                alert("Por favor, digite um termo para busca!");
                return;
            }
            const newLimitVal = document.getElementById("new-query-limit")?.value || "5";
            
            currentQuery = newQueryVal;
            
            // Silently update address bar query param so we store results under correct key
            const newUrl = `${window.location.protocol}//${window.location.host}${window.location.pathname}?q=${encodeURIComponent(currentQuery)}`;
            window.history.pushState({ path: newUrl }, '', newUrl);
            
            // Clean local analysis list for the new run
            localAnalysisResults = [];
            
            // Remove the placeholder option if it exists when starting a real analysis
            if (querySelect) {
                const placeholderOpt = Array.from(querySelect.options).find(opt => opt.value === "");
                if (placeholderOpt) {
                    placeholderOpt.remove();
                }
            }
            
            appendLog(`[Console] Solicitando início da busca para: '${currentQuery}' (${newLimitVal} links)...`);
            const fetchProtocol = window.location.protocol === "https:" ? "https:" : "http:";
            fetch(`${fetchProtocol}//${backendHost}/api/start?query=${encodeURIComponent(currentQuery)}&limit=${newLimitVal}`, { method: "POST" })
                .then(r => r.json())
                .then(data => {
                    appendLog(`[Console] Servidor respondeu: ${data.message}`);
                })
                .catch(err => {
                    appendLog(`[Console] Erro ao iniciar: ${err}`);
                });
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            if (confirm("Deseja realmente limpar TODOS os dados de análises e relatórios salvos no navegador? Esta ação não pode ser desfeita.")) {
                localStorage.removeItem("analysisResults");
                localStorage.removeItem("consolidatedReport");
                localStorage.removeItem("consolidatedReportTime");
                localStorage.removeItem("reputation_analyses_store");
                appendLog("[Console] Cache local limpo. Recarregando página...");
                window.location.reload();
            }
        });
    }

    // Connect WebSockets
    initWebSocket();

    // Initialize App
    calculateKPIs(errorFreeData);
    updateResultsList();

    // Event Listeners
    searchBox.addEventListener("input", filterResults);
    downloadPdfBtn.addEventListener("click", downloadPDF);
    
    // Scroll event for back to top button
    window.addEventListener("scroll", () => {
        if (window.scrollY > 300) {
            backToTopBtn.classList.add("show");
        } else {
            backToTopBtn.classList.remove("show");
        }
    });

    backToTopBtn.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Helper functions
    function extractDomain(url) {
        try {
            const parsed = new URL(url);
            return parsed.hostname.replace('www.', '');
        } catch (e) {
            return "link-externo";
        }
    }

    function calculateKPIs(results) {
        kpiTotal.textContent = results.length;
        
        const domains = new Set();
        let socialCount = 0;

        results.forEach(item => {
            const domain = extractDomain(item.url);
            domains.add(domain);

            // Social Media detection
            if (domain.includes("linkedin.com") ||
                domain.includes("instagram.com") ||
                domain.includes("facebook.com") ||
                domain.includes("youtube.com") ||
                domain.includes("tiktok.com") ||
                domain.includes("twitter.com") ||
                domain.includes("x.com")) {
                socialCount++;
            }
        });

        kpiDomains.textContent = domains.size;
        kpiSocial.textContent = socialCount;
    }

    function updateResultsList() {
        renderResultsSlice();
        renderPaginationControls();
    }

    function renderResultsSlice() {
        resultsContainer.innerHTML = "";
        
        if (filteredData.length === 0) {
            resultsContainer.innerHTML = `
                <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                    <svg width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="margin-bottom: 1rem;"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg>
                    <p style="font-size: 1.1rem; font-weight: 500;">Nenhum resultado encontrado</p>
                    <p style="font-size: 0.9rem; margin-top: 0.3rem;">Tente buscar por termos diferentes.</p>
                </div>
            `;
            resultsCountText.textContent = "Exibindo 0 de 0 resultados";
            paginationContainer.innerHTML = "";
            return;
        }

        const startIdx = (currentPage - 1) * itemsPerPage;
        const endIdx = Math.min(startIdx + itemsPerPage, filteredData.length);
        const pageItems = filteredData.slice(startIdx, endIdx);

        resultsCountText.textContent = `Exibindo ${startIdx + 1}-${endIdx} de ${filteredData.length} resultados`;

        pageItems.forEach(item => {
            const domain = extractDomain(item.url);
            const card = document.createElement("div");
            card.className = "result-card";
            card.setAttribute("data-rank", item.rank);
            
            // Build Base HTML
            let htmlContent = `
                <div class="rank-container">
                    <div class="rank-badge" title="Posição orgânica: ${item.rank}">${item.rank}</div>
                </div>
                <div class="card-content">
                    <div class="card-header">
                        <a href="${item.url}" target="_blank" class="card-title" rel="noopener noreferrer">${escapeHtml(item.title)}</a>
                        <div class="header-badges">
                            ${item.data_hora ? `<span class="time-badge">⏱️ ${escapeHtml(item.data_hora)}</span>` : ''}
                            <span class="domain-badge">${domain}</span>
                        </div>
                    </div>
                    <div class="url-bar">
                        <a href="${item.url}" target="_blank" class="url-link" rel="noopener noreferrer">${item.url}</a>
                        <button class="copy-btn" data-url="${item.url}" title="Copiar URL">
                            <svg class="copy-icon" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path></svg>
                            <svg class="check-icon" width="14" height="14" fill="none" stroke="var(--success)" stroke-width="2.5" viewBox="0 0 24 24" style="display: none;"><path d="M20 6 9 17l-5-5"></path></svg>
                        </button>
                    </div>
            `;

            // If AI analysis is present, append the details block (collapsed by default)
            if (isAiLoaded) {
                const categoryClass = item.categoria === "Erro de Acesso" ? "access-error" : "";
                
                htmlContent += `
                    <!-- AI Details Accordion Block -->
                    <button class="expand-toggle" data-target="details-${item.rank}">
                        <span>Ver detalhes da análise</span>
                        <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path d="m19 9-7 7-7-7"></path></svg>
                    </button>
                    
                    <div class="ai-analysis-block" id="details-${item.rank}">
                        <div class="ai-item">
                            <div class="ai-label">📂 Categoria / Tema</div>
                            <div class="ai-value category-theme">
                                <span class="badge-tag ${categoryClass}">${escapeHtml(item.categoria)}</span>
                                <span class="badge-tag theme">${escapeHtml(item.tema)}</span>
                            </div>
                        </div>
                        <div class="ai-item-full">
                            <div class="ai-label">📝 Resumo Analítico</div>
                            <div class="ai-value">${escapeHtml(item.resumo)}</div>
                        </div>
                        <div class="ai-item highlight-positive">
                            <div class="ai-label">✨ Destaques Positivos</div>
                            <div class="ai-value">${escapeHtml(item.destaques_positivos)}</div>
                        </div>
                        <div class="ai-item highlight-negative">
                            <div class="ai-label">⚠️ Destaques Negativos</div>
                            <div class="ai-value">${escapeHtml(item.destaques_negativos)}</div>
                        </div>
                        <div class="ai-timestamp" style="grid-column: 1 / -1;">
                            Analisado em: ${item.data_hora}
                        </div>
                    </div>
                `;
            } else {
                htmlContent += `
                    <p class="card-snippet">${escapeHtml(item.snippet || "Sem descrição disponível.")}</p>
                `;
            }

            htmlContent += `</div>`;
            card.innerHTML = htmlContent;
            
            // Add expand/collapse accordion listener
            if (isAiLoaded) {
                const expandToggle = card.querySelector(".expand-toggle");
                const detailsBlock = card.querySelector(".ai-analysis-block");
                
                expandToggle.addEventListener("click", () => {
                    const isShown = detailsBlock.classList.toggle("show");
                    expandToggle.classList.toggle("active");
                    
                    const labelSpan = expandToggle.querySelector("span");
                    if (isShown) {
                        labelSpan.textContent = "Ocultar detalhes";
                    } else {
                        labelSpan.textContent = "Ver detalhes da análise";
                    }
                });
            }

            // Copy button listener
            const copyBtn = card.querySelector(".copy-btn");
            const copyIcon = card.querySelector(".copy-icon");
            const checkIcon = card.querySelector(".check-icon");
            
            copyBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                const url = copyBtn.getAttribute("data-url");
                navigator.clipboard.writeText(url).then(() => {
                    copyIcon.style.display = "none";
                    checkIcon.style.display = "block";
                    setTimeout(() => {
                        copyIcon.style.display = "block";
                        checkIcon.style.display = "none";
                    }, 2000);
                });
            });

            resultsContainer.appendChild(card);
        });
    }

    function renderPaginationControls() {
        paginationContainer.innerHTML = "";
        
        const totalPages = Math.ceil(filteredData.length / itemsPerPage);
        if (totalPages <= 1) return;

        // Previous button
        const prevBtn = document.createElement("button");
        prevBtn.className = "page-btn";
        prevBtn.disabled = currentPage === 1;
        prevBtn.innerHTML = `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path d="m15 19-7-7 7-7"></path></svg>`;
        prevBtn.addEventListener("click", () => {
            if (currentPage > 1) {
                currentPage--;
                updateResultsList();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
        paginationContainer.appendChild(prevBtn);

        // Page Numbers
        for (let i = 1; i <= totalPages; i++) {
            const pageBtn = document.createElement("button");
            pageBtn.className = `page-btn ${currentPage === i ? 'active' : ''}`;
            pageBtn.textContent = i;
            pageBtn.addEventListener("click", () => {
                currentPage = i;
                updateResultsList();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });
            paginationContainer.appendChild(pageBtn);
        }

        // Next button
        const nextBtn = document.createElement("button");
        nextBtn.className = "page-btn";
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.innerHTML = `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path d="m9 5 7 7-7 7"></path></svg>`;
        nextBtn.addEventListener("click", () => {
            if (currentPage < totalPages) {
                currentPage++;
                updateResultsList();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
        paginationContainer.appendChild(nextBtn);
    }

    function filterResults() {
        const query = searchBox.value.toLowerCase().trim();
        currentPage = 1; // Reset to page 1 on search
        
        if (!query) {
            filteredData = [...errorFreeData];
            updateResultsList();
            return;
        }

        filteredData = errorFreeData.filter(item => {
            const title = item.title.toLowerCase();
            const url = item.url.toLowerCase();
            const domain = extractDomain(item.url).toLowerCase();
            
            let match = title.includes(query) || url.includes(query) || domain.includes(query);
            
            if (isAiLoaded) {
                const summary = (item.resumo || "").toLowerCase();
                const category = (item.categoria || "").toLowerCase();
                const theme = (item.tema || "").toLowerCase();
                const positive = (item.destaques_positivos || "").toLowerCase();
                const negative = (item.destaques_negativos || "").toLowerCase();
                
                match = match || summary.includes(query) || category.includes(query) || 
                        theme.includes(query) || positive.includes(query) || negative.includes(query);
            } else {
                const snippet = (item.snippet || "").toLowerCase();
                match = match || snippet.includes(query);
            }

            return match;
        });

        updateResultsList();
    }

    // Render consolidated report tab
    function renderConsolidatedReport() {
        const cachedReport = activeQueryData.report || "";
        if (!cachedReport) {
            reportContainer.innerHTML = `
                <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                    <p style="font-size: 1.1rem; font-weight: 500;">Relatório consolidado não disponível para esta consulta</p>
                    <p style="font-size: 0.9rem; margin-top: 0.3rem;">Execute uma análise no servidor para gerar o relatório com IA.</p>
                </div>
            `;
            return;
        }
        
        let html = cachedReport;
        
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
        
        const lines = html.split('\n');
        const paragraphLines = lines.map(line => {
            const trimmed = line.strip ? line.strip() : line.trim();
            if (!trimmed) return "";
            if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('<li') || trimmed.startsWith('</ul')) {
                return line;
            }
            return `<p>${line}</p>`;
        });
        
        let reportHtml = paragraphLines.join('\n');
        
        // Add a nice header badge for the consolidated timestamp
        const reportTime = activeQueryData.reportTime;
        if (reportTime) {
            reportHtml = `<div class="report-timestamp-badge">📅 Relatório Consolidado Gerado em: ${reportTime}</div>` + reportHtml;
        }
        
        reportContainer.innerHTML = reportHtml;
    }

    // Render Connection/Access Errors Tab
    function renderErrorsList() {
        if (!errorsContainer) return;
        errorsContainer.innerHTML = "";
        
        const errorItems = data.filter(item => isAccessError(item));
        
        if (errorsCountText) {
            errorsCountText.textContent = `Exibindo ${errorItems.length} de ${data.length} URLs com Erro de Conexão/Acesso`;
        }
        
        if (errorItems.length === 0) {
            errorsContainer.innerHTML = `
                <div style="text-align: center; padding: 3rem; color: var(--text-secondary);">
                    <svg width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="margin-bottom: 1rem;"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <p style="font-size: 1.1rem; font-weight: 500;">Nenhum erro de conexão/acesso identificado</p>
                </div>
            `;
            return;
        }
        
        errorItems.forEach(item => {
            const domain = extractDomain(item.url);
            const card = document.createElement("div");
            card.className = "result-card";
            card.setAttribute("data-rank", item.rank);
            
            const categoryClass = "access-error";
            
            card.innerHTML = `
                <div class="rank-container">
                    <div class="rank-badge" title="Posição orgânica: ${item.rank}">${item.rank}</div>
                </div>
                <div class="card-content">
                    <div class="card-header">
                        <a href="${item.url}" target="_blank" class="card-title" rel="noopener noreferrer">${escapeHtml(item.title)}</a>
                        <div class="header-badges">
                            ${item.data_hora ? `<span class="time-badge">⏱️ ${escapeHtml(item.data_hora)}</span>` : ''}
                            <span class="domain-badge">${domain}</span>
                        </div>
                    </div>
                    <div class="url-bar">
                        <a href="${item.url}" target="_blank" class="url-link" rel="noopener noreferrer">${item.url}</a>
                        <button class="copy-btn" data-url="${item.url}" title="Copiar URL">
                            <svg class="copy-icon" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path></svg>
                            <svg class="check-icon" width="14" height="14" fill="none" stroke="var(--success)" stroke-width="2.5" viewBox="0 0 24 24" style="display: none;"><path d="M20 6 9 17l-5-5"></path></svg>
                        </button>
                    </div>
                    
                    <button class="expand-toggle" data-target="err-details-${item.rank}">
                        <span>Ver detalhes do erro</span>
                        <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path d="m19 9-7 7-7-7"></path></svg>
                    </button>
                    
                    <div class="ai-analysis-block" id="err-details-${item.rank}">
                        <div class="ai-item">
                            <div class="ai-label">📂 Categoria / Tema</div>
                            <div class="ai-value category-theme">
                                <span class="badge-tag ${categoryClass}">${escapeHtml(item.categoria)}</span>
                                <span class="badge-tag theme">${escapeHtml(item.tema)}</span>
                            </div>
                        </div>
                        <div class="ai-item-full">
                            <div class="ai-label">📝 Resumo / Detalhes da Falha</div>
                            <div class="ai-value">${escapeHtml(item.resumo)}</div>
                        </div>
                        <div class="ai-timestamp" style="grid-column: 1 / -1;">
                            Tentativa de análise em: ${item.data_hora}
                        </div>
                    </div>
                </div>
            `;
            
            const expandToggle = card.querySelector(".expand-toggle");
            const detailsBlock = card.querySelector(".ai-analysis-block");
            
            expandToggle.addEventListener("click", () => {
                const isShown = detailsBlock.classList.toggle("show");
                expandToggle.classList.toggle("active");
                const labelSpan = expandToggle.querySelector("span");
                labelSpan.textContent = isShown ? "Ocultar detalhes" : "Ver detalhes do erro";
            });
            
            const copyBtn = card.querySelector(".copy-btn");
            const copyIcon = card.querySelector(".copy-icon");
            const checkIcon = card.querySelector(".check-icon");
            
            copyBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                const url = copyBtn.getAttribute("data-url");
                navigator.clipboard.writeText(url).then(() => {
                    copyIcon.style.display = "none";
                    checkIcon.style.display = "block";
                    setTimeout(() => {
                        copyIcon.style.display = "block";
                        checkIcon.style.display = "none";
                    }, 2000);
                });
            });
            
            errorsContainer.appendChild(card);
        });
    }

    // Custom PDF Exporter combining both Report and complete Results Table
    function downloadPDF() {
        const printWindow = window.open('', '_blank');
        
        let consolidatedReportHtml = "";
        if (isAiLoaded) {
            consolidatedReportHtml = reportContainer.innerHTML;
        } else {
            consolidatedReportHtml = "<h1>Relatório Consolidado não gerado</h1><p>Por favor, execute o script 'analyze.py' para gerar o relatório consolidado de reputação.</p>";
        }

        let printHtml = `
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <title>Relatório de Reputação Digital - Marcelo Baptista de Oliveira</title>
            <style>
                body {
                    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                    padding: 40px;
                    color: #1f2937;
                    line-height: 1.6;
                    background-color: #ffffff;
                }
                .section {
                    margin-bottom: 50px;
                    page-break-after: always;
                }
                h1 {
                    text-align: center;
                    font-size: 26px;
                    color: #111827;
                    border-bottom: 2px solid #8b5cf6;
                    padding-bottom: 15px;
                    margin-bottom: 30px;
                }
                h2 {
                    font-size: 18px;
                    color: #7c3aed;
                    margin-top: 30px;
                    border-bottom: 1px solid #e5e7eb;
                    padding-bottom: 8px;
                }
                p, li {
                    font-size: 14px;
                    color: #4b5563;
                }
                ul {
                    padding-left: 20px;
                }
                li {
                    margin-bottom: 8px;
                }
                strong {
                    color: #111827;
                }
                
                /* Results style */
                .results-header-title {
                    text-align: center;
                    font-size: 22px;
                    color: #111827;
                    margin-bottom: 25px;
                    border-bottom: 2px solid #8b5cf6;
                    padding-bottom: 10px;
                }
                .result-card {
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 16px;
                    page-break-inside: avoid;
                    background-color: #fafafa;
                }
                .card-header {
                    display: flex;
                    justify-content: space-between;
                    font-weight: 700;
                    font-size: 14px;
                    color: #111827;
                    border-bottom: 1px solid #e5e7eb;
                    padding-bottom: 6px;
                    margin-bottom: 10px;
                }
                .rank {
                    color: #7c3aed;
                }
                .url {
                    color: #0891b2;
                    font-size: 13px;
                    word-break: break-all;
                    margin-bottom: 8px;
                    font-weight: 500;
                }
                .snippet {
                    font-size: 13px;
                    color: #4b5563;
                }
                .ai-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                    margin-top: 12px;
                    font-size: 13px;
                }
                .ai-cell {
                    background-color: #ffffff;
                    border: 1px solid #e5e7eb;
                    padding: 10px;
                    border-radius: 6px;
                }
                .ai-cell-full {
                    grid-column: 1 / -1;
                    background-color: #ffffff;
                    border: 1px solid #e5e7eb;
                    padding: 10px;
                    border-radius: 6px;
                }
                .label {
                    font-weight: 700;
                    color: #6b7280;
                    font-size: 10px;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: 4px;
                }
                .positive {
                    border-left: 3px solid #10b981;
                }
                .negative {
                    border-left: 3px solid #ef4444;
                }
                .timestamp {
                    font-size: 11px;
                    color: #9ca3af;
                    text-align: right;
                    margin-top: 8px;
                    font-style: italic;
                }
            </style>
        </head>
        <body>
            <!-- Section 1: General Consolidated Analysis -->
            <div class="section">
                ${consolidatedReportHtml}
            </div>
            
            <!-- Section 2: Results Table (All 100 links fully detailed) -->
            <div>
                <h1 class="results-header-title">Tabela de Resultados Orgânicos (Top 100)</h1>
        `;

        errorFreeData.forEach(item => {
            const domain = extractDomain(item.url);
            printHtml += `
                <div class="result-card">
                    <div class="card-header">
                        <span class="rank">#${item.rank} - ${escapeHtml(item.title)}</span>
                        <span style="font-weight: 500; font-size: 12px; color: #6b7280;">${domain}</span>
                    </div>
                    <div class="url">${item.url}</div>
            `;

            if (isAiLoaded) {
                printHtml += `
                    <div class="ai-grid">
                        <div class="ai-cell">
                            <div class="label">📂 Categoria</div>
                            <div>${escapeHtml(item.categoria)}</div>
                        </div>
                        <div class="ai-cell">
                            <div class="label">🏷️ Tema</div>
                            <div>${escapeHtml(item.tema)}</div>
                        </div>
                        <div class="ai-cell-full">
                            <div class="label">📝 Resumo Analítico</div>
                            <div>${escapeHtml(item.resumo)}</div>
                        </div>
                        <div class="ai-cell positive">
                            <div class="label">✨ Destaques Positivos</div>
                            <div>${escapeHtml(item.destaques_positivos)}</div>
                        </div>
                        <div class="ai-cell negative">
                            <div class="label">⚠️ Destaques Negativos</div>
                            <div>${escapeHtml(item.destaques_negativos)}</div>
                        </div>
                    </div>
                    <div class="timestamp">Analisado em: ${item.data_hora}</div>
                `;
            } else {
                printHtml += `
                    <div class="snippet">${escapeHtml(item.snippet || "Sem descrição disponível.")}</div>
                `;
            }

            printHtml += `</div>`;
        });

        printHtml += `
            </div>
        </body>
        </html>
        `;

        printWindow.document.write(printHtml);
        printWindow.document.close();
        printWindow.focus();
        
        // Timeout to ensure print window finishes rendering
        setTimeout(() => {
            printWindow.print();
        }, 800);
    }

    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text ? text.replace(/[&<>"']/g, m => map[m]) : "";
    }
});
