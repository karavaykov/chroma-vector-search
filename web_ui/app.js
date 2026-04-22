document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const searchInput = document.getElementById('search-query');
    const searchBtn = document.getElementById('btn-search');
    const searchType = document.getElementById('search-type');
    const semanticWeight = document.getElementById('semantic-weight');
    const keywordWeight = document.getElementById('keyword-weight');
    const semanticWeightVal = document.getElementById('semantic-weight-val');
    const keywordWeightVal = document.getElementById('keyword-weight-val');
    const nResults = document.getElementById('n-results');
    
    const projectRoot = document.getElementById('project-root');
    const indexBtn = document.getElementById('btn-index');
    const progressContainer = document.getElementById('indexing-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressDetails = document.getElementById('progress-details');
    
    const resultsContainer = document.getElementById('results-container');
    const searchStats = document.getElementById('search-stats');
    const resultCount = document.getElementById('result-count');
    const searchTime = document.getElementById('search-time');
    
    const wsStatus = document.getElementById('ws-status');
    const wsStatusText = document.getElementById('ws-status-text');
    
    const statDevice = document.getElementById('stat-device');
    const statCollection = document.getElementById('stat-collection');
    const statDocs = document.getElementById('stat-docs');
    
    const resultTemplate = document.getElementById('result-template');

    // API Configuration
    const API_URL = window.location.protocol === 'file:' ? 'http://localhost:8000' : window.location.origin;
    const WS_URL = `ws://${window.location.hostname === '' ? 'localhost' : window.location.hostname}:8766`;
    let ws = null;

    // Initialize
    initWebSocket();
    setupEventListeners();

    // Event Listeners
    function setupEventListeners() {
        // Search
        searchBtn.addEventListener('click', performSearch);
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });

        // Indexing
        indexBtn.addEventListener('click', startIndexing);

        // Hybrid Settings
        searchType.addEventListener('change', (e) => {
            const isHybrid = e.target.value === 'hybrid';
            document.querySelectorAll('.hybrid-settings').forEach(el => {
                el.style.display = isHybrid ? 'block' : 'none';
            });
        });

        semanticWeight.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            semanticWeightVal.textContent = val.toFixed(1);
            keywordWeight.value = (1 - val).toFixed(1);
            keywordWeightVal.textContent = (1 - val).toFixed(1);
        });

        keywordWeight.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            keywordWeightVal.textContent = val.toFixed(1);
            semanticWeight.value = (1 - val).toFixed(1);
            semanticWeightVal.textContent = (1 - val).toFixed(1);
        });
    }

    // WebSocket Connection
    function initWebSocket() {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            wsStatus.className = 'status-dot online';
            wsStatusText.textContent = 'Connected';
            
            // Request initial stats
            ws.send(JSON.stringify({ type: 'stats' }));
        };

        ws.onclose = () => {
            wsStatus.className = 'status-dot offline';
            wsStatusText.textContent = 'Disconnected';
            // Try to reconnect after 5 seconds
            setTimeout(initWebSocket, 5000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket Error:', error);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (e) {
                console.error('Error parsing WS message:', e);
            }
        };
    }

    function handleWebSocketMessage(message) {
        switch (message.type) {
            case 'stats':
                updateStats(message.data);
                break;
            case 'progress':
                updateProgress(message.data);
                break;
            case 'search_results':
                renderResults(message.data);
                break;
            case 'error':
                showError(message.error);
                break;
        }
    }

    // Actions
    async function performSearch() {
        const query = searchInput.value.trim();
        if (!query) return;

        searchBtn.disabled = true;
        searchBtn.textContent = 'Searching...';
        resultsContainer.innerHTML = '<div class="empty-state"><p>Searching...</p></div>';
        searchStats.classList.add('hidden');

        const payload = {
            query: query,
            n_results: parseInt(nResults.value) || 10,
            search_type: searchType.value
        };

        if (searchType.value === 'hybrid') {
            payload.semantic_weight = parseFloat(semanticWeight.value);
            payload.keyword_weight = parseFloat(keywordWeight.value);
        }

        try {
            // Try WebSocket first if connected
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'search',
                    data: payload
                }));
            } else {
                // Fallback to REST API
                const response = await fetch(`${API_URL}/api/v1/search`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                renderResults(data);
            }
        } catch (error) {
            showError(`Search failed: ${error.message}`);
            searchBtn.disabled = false;
            searchBtn.textContent = 'Search';
        }
    }

    async function startIndexing() {
        const path = projectRoot.value.trim();
        if (!path) {
            alert('Please enter a project root path');
            return;
        }

        indexBtn.disabled = true;
        progressContainer.classList.remove('hidden');
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        progressDetails.textContent = 'Starting indexing...';
        wsStatus.className = 'status-dot indexing';

        try {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'index',
                    data: { project_root: path }
                }));
            } else {
                const response = await fetch(`${API_URL}/api/v1/index`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_root: path })
                });
                
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data = await response.json();
                progressDetails.textContent = data.message || 'Indexing completed';
                progressFill.style.width = '100%';
                progressText.textContent = '100%';
                setTimeout(() => {
                    indexBtn.disabled = false;
                    wsStatus.className = 'status-dot online';
                }, 2000);
            }
        } catch (error) {
            showError(`Indexing failed: ${error.message}`);
            indexBtn.disabled = false;
            wsStatus.className = 'status-dot online';
        }
    }

    // UI Updates
    function updateStats(data) {
        if (data.device) statDevice.textContent = data.device;
        if (data.collection) statCollection.textContent = data.collection;
        if (data.document_count !== undefined) statDocs.textContent = data.document_count.toLocaleString();
    }

    function updateProgress(data) {
        if (data.status === 'indexing') {
            const percent = Math.round((data.processed / data.total) * 100) || 0;
            progressFill.style.width = `${percent}%`;
            progressText.textContent = `${percent}%`;
            progressDetails.textContent = `Processing file ${data.processed} of ${data.total}`;
        } else if (data.status === 'completed') {
            progressFill.style.width = '100%';
            progressText.textContent = '100%';
            progressDetails.textContent = `Completed in ${data.time_taken_seconds.toFixed(1)}s`;
            indexBtn.disabled = false;
            wsStatus.className = 'status-dot online';
            
            // Refresh stats
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'stats' }));
            }
        } else if (data.status === 'error') {
            showError(data.message);
            indexBtn.disabled = false;
            wsStatus.className = 'status-dot online';
        }
    }

    function renderResults(data) {
        searchBtn.disabled = false;
        searchBtn.textContent = 'Search';
        
        resultsContainer.innerHTML = '';
        
        if (!data.results || data.results.length === 0) {
            resultsContainer.innerHTML = '<div class="empty-state"><p>No results found</p></div>';
            searchStats.classList.add('hidden');
            return;
        }

        // Update stats
        resultCount.textContent = data.results.length;
        searchTime.textContent = (data.time_taken_seconds * 1000).toFixed(0);
        searchStats.classList.remove('hidden');

        data.results.forEach(result => {
            const clone = resultTemplate.content.cloneNode(true);
            
            // File path and score
            clone.querySelector('.file-path').textContent = result.file_path;
            clone.querySelector('.result-score').textContent = `Score: ${result.score.toFixed(3)}`;
            
            // Code content
            const codeBlock = clone.querySelector('code');
            codeBlock.textContent = result.content;
            
            // Lines info
            if (result.line_start && result.line_end) {
                clone.querySelector('.lines-info').textContent = `Lines: ${result.line_start} - ${result.line_end}`;
            }

            // Metadata badges
            if (result.metadata) {
                const metaContainer = clone.querySelector('.result-metadata');
                let hasMetadata = false;

                // 1C specific metadata
                if (result.metadata.object_type) {
                    const badge = document.createElement('span');
                    badge.className = `badge type-${result.metadata.object_type.toLowerCase()}`;
                    badge.textContent = `${result.metadata.object_type}: ${result.metadata.object_name || 'Unknown'}`;
                    metaContainer.appendChild(badge);
                    hasMetadata = true;
                }

                if (result.metadata.module_type) {
                    const badge = document.createElement('span');
                    badge.className = `badge module-${result.metadata.module_type.toLowerCase()}`;
                    badge.textContent = result.metadata.module_type;
                    metaContainer.appendChild(badge);
                    hasMetadata = true;
                }

                if (result.metadata.author) {
                    const badge = document.createElement('span');
                    badge.className = 'badge author';
                    badge.textContent = `👤 ${result.metadata.author}`;
                    metaContainer.appendChild(badge);
                    hasMetadata = true;
                }

                if (result.metadata.calls && result.metadata.calls !== "[]") {
                    try {
                        const calls = JSON.parse(result.metadata.calls);
                        if (calls.length > 0) {
                            const badge = document.createElement('span');
                            badge.className = 'badge';
                            badge.textContent = `Calls: ${calls.length} functions`;
                            badge.title = calls.join(', ');
                            metaContainer.appendChild(badge);
                            hasMetadata = true;
                        }
                    } catch(e) {}
                }

                if (hasMetadata) {
                    metaContainer.classList.remove('hidden');
                }
            }

            // Copy button
            const copyBtn = clone.querySelector('.btn-copy');
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(result.content).then(() => {
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => copyBtn.textContent = 'Copy', 2000);
                });
            });

            resultsContainer.appendChild(clone);
        });

        // Apply syntax highlighting
        document.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }

    function showError(message) {
        console.error(message);
        alert(`Error: ${message}`);
    }
});