let ws = null;
let term = null;
let fitAddon = null;
let webglAddon = null; // Added to track WebGL addon

// Toast Notification System
// Toast Notification System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ',
        warning: '⚠'
    };
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('toast-show'), 10);
    setTimeout(() => {
        toast.classList.remove('toast-show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Filter Management
const filterInput = document.getElementById('filter');
const searchCount = document.getElementById('search-count');
const categoryFilter = document.getElementById('category-filter');
const imageCards = document.querySelectorAll('.image-card');
const filterButtons = document.querySelectorAll('.filter-btn');
let activeStatusFilter = 'all';

// Update counts for all, running, and stopped containers
function updateCounts() {
    let allCount = 0;
    let runningCount = 0;
    let stoppedCount = 0;

    imageCards.forEach(card => {
        const status = card.querySelector('.status-text').textContent.toLowerCase();
        if (status === 'running') {
            runningCount++;
        } else {
            stoppedCount++;
        }
        if (card.style.display !== 'none') {
            allCount++;
        }
    });

    document.getElementById('count-all').textContent = allCount;
    document.getElementById('count-running').textContent = runningCount;
    document.getElementById('count-stopped').textContent = stoppedCount;
    searchCount.textContent = `${allCount} of ${imageCards.length} containers`;
}

// Apply all filters (search, status, category)
function applyFilters() {
    const searchTerm = filterInput.value.toLowerCase();
    const selectedCategory = categoryFilter.value.toLowerCase();

    imageCards.forEach(card => {
        const name = card.getAttribute('data-name').toLowerCase();
        const category = card.getAttribute('data-category').toLowerCase();
        const status = card.querySelector('.status-text').textContent.toLowerCase();

        const matchesSearch = searchTerm ? (name.includes(searchTerm) || category.includes(searchTerm)) : true;
        const matchesCategory = selectedCategory ? category === selectedCategory : true;
        const matchesStatus = activeStatusFilter === 'all' ? true : status === activeStatusFilter;

        card.style.display = matchesSearch && matchesCategory && matchesStatus ? '' : 'none';
    });

    updateCounts();
}

// Filter by status
function filterByStatus(status) {
    activeStatusFilter = status;

    filterButtons.forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-filter') === status);
    });

    applyFilters();
}

// Filter by category
function filterByCategory(category) {
    applyFilters();
}

// Stop all running containers
async function stopAllRunning() {
    //console.log('stopAllRunning: Started at', new Date().toISOString());
    try {
        const confirmed = await showConfirmModal(
            'Stop All Containers',
            'Are you sure you want to stop ALL running containers?',
            'danger'
        );
        //console.log('stopAllRunning: Confirmation:', confirmed);
        if (!confirmed) {
            //console.log('stopAllRunning: Cancelled by user');
            return;
        }

        showLoader('Stopping all containers...');
        showToast('Stopping all containers...', 'info');
        //console.log('stopAllRunning: Sending POST to /api/stop-all');

        const controller = new AbortController();
        const startTime = Date.now();
        const timeoutId = setTimeout(() => {
            //console.log('stopAllRunning: Timeout after 120s, elapsed:', (Date.now() - startTime) / 1000 + 's');
            controller.abort();
        }, 120000);

        try {
            const response = await fetch('/api/stop-all', {
                method: 'POST',
                signal: controller.signal
            });
            const responseTime = (Date.now() - startTime) / 1000;
            //console.log('stopAllRunning: Response received after', responseTime + 's', { status: response.status });
            clearTimeout(timeoutId);

            const data = await response.json();
            //console.log('stopAllRunning: Response data:', JSON.stringify(data, null, 2));

            if (response.ok) {
                showToast(`Successfully stopped ${data.stopped} containers`, 'success');
                //console.log('stopAllRunning: Success, reloading in 2s');
                setTimeout(() => {
                    //console.log('stopAllRunning: Reloading page');
                    location.reload();
                }, 2000);
            } else {
                showToast('Failed to stop all containers', 'error');
                //console.log('stopAllRunning: Failed, status:', response.status, { error: data });
                hideLoader();
            }
        } catch (fetchError) {
            //console.log('stopAllRunning: Fetch error:', fetchError, { elapsed: (Date.now() - startTime) / 1000 + 's' });
            clearTimeout(timeoutId);
            if (fetchError.name === 'AbortError') {
                showToast('Operation timeout - please wait and refresh manually', 'warning');
                //console.log('stopAllRunning: Timeout error (AbortError)');
            } else {
                showToast(`Error: ${fetchError.message}`, 'error');
                //console.log('stopAllRunning: Other error:', fetchError.message);
            }
            hideLoader();
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
        //console.log('stopAllRunning: General error:', e);
        hideLoader();
    }
}

// Update card UI after state change
function updateCardUI(imageName, isRunning, containerName) {
    const card = document.querySelector(`[data-name="${imageName}"]`);
    if (!card) return;

    const statusIndicator = card.querySelector('.status-indicator');
    const statusText = card.querySelector('.status-text');
    const actions = card.querySelector('.card-actions');

    if (isRunning) {
        card.setAttribute('data-container', containerName);
        statusIndicator.className = 'status-indicator status-running';
        statusText.textContent = 'Running';
        actions.innerHTML = `
            <button class="btn btn-danger" onclick="stopContainer('${imageName}', '${containerName}')">
                <span class="btn-icon">⏹</span> Stop
            </button>
            <button class="btn btn-primary" onclick="showLogs('${containerName}')">
                <span class="btn-icon">📋</span> Logs
            </button>
            <button class="btn btn-success" onclick="openConsole('${containerName}', '${imageName}')">
                <span class="btn-icon">💻</span> Console
            </button>
        `;
    } else {
        card.removeAttribute('data-container');
        statusIndicator.className = 'status-indicator status-stopped';
        statusText.textContent = 'Stopped';
        actions.innerHTML = `
            <button class="btn btn-success btn-block" onclick="startContainer('${imageName}')">
                <span class="btn-icon">▶</span> Start Container
            </button>
        `;
    }

    applyFilters();
}

// Start Container (AJAX)
async function startContainer(image) {
    const card = document.querySelector(`[data-name="${image}"]`);
    const btn = card.querySelector('.btn-success');
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Starting...';

    try {
        showLoader(`Starting container ${image}...`);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 35000);

        const response = await fetch(`/start/${image}`, {
            method: 'POST',
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        const data = await response.json();

        if (response.ok && data.ready) {
            showToast(`Container ${data.container} started successfully`, 'success');
            updateCardUI(image, true, data.container);
        } else if (response.ok) {
            showToast(`Container ${data.container} is starting...`, 'info');
            btn.innerHTML = '<span class="spinner"></span> Please wait...';
            pollContainerStatus(image, btn);
        } else {
            const errorMsg = data.detail || 'Failed to start container';
            showToast(`Error: ${errorMsg}`, 'error');
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }
    } catch (e) {
        if (e.name === 'AbortError') {
            showToast(`Timeout starting ${image} - check container logs`, 'warning');
            setTimeout(() => location.reload(), 2000);
        } else {
            showToast(`Error: ${e.message}`, 'error');
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }
    } finally {
        hideLoader();
    }
}

// Poll container status after start
async function pollContainerStatus(image, btn) {
    let attempts = 0;
    const maxAttempts = 20;

    const poll = async () => {
        try {
            const response = await fetch('/');
            const text = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');
            const newCard = doc.querySelector(`[data-name="${image}"]`);

            if (newCard) {
                const statusText = newCard.querySelector('.status-text').textContent;
                if (statusText === 'Running') {
                    showToast(`Container ${image} is now ready!`, 'success');
                    location.reload();
                    return;
                }
            }

            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 500);
            } else {
                showToast(`Container may still be starting - refresh page to check`, 'warning');
                btn.disabled = false;
                btn.innerHTML = '<span class="btn-icon">▶</span> Start Container';
            }
        } catch (e) {
            console.error('Poll error:', e);
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 500);
            }
        }
    };

    poll();
}

// Stop Container (AJAX)
async function stopContainer(imageName, containerName) {
    try {
        const confirmed = await showConfirmModal(
            'Stop Container',
            `Are you sure you want to stop container ${containerName}?`
        );
        if (!confirmed) return;

        const card = document.querySelector(`[data-name="${imageName}"]`);
        const btn = card.querySelector('.btn-danger');
        const originalHTML = btn.innerHTML; // SALVA SUBITO
        
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Stopping...';

        showLoader(`Stopping container ${containerName}...`);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minuti

        try {
            const response = await fetch(`/stop/${containerName}`, { 
                method: 'POST',
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (response.ok) {
                showToast(`Container ${containerName} stopped`, 'success');
                updateCardUI(imageName, false, '');
            } else {
                const data = await response.json();
                const errorMsg = data.detail || 'Failed to stop container';
                showToast(`Error: ${errorMsg}`, 'error');
                btn.disabled = false;
                btn.innerHTML = originalHTML;
            }
        } catch (fetchError) {
            clearTimeout(timeoutId);
            
            if (fetchError.name === 'AbortError') {
                showToast(`Timeout stopping ${containerName} - container may still be stopping`, 'warning');
                // Mostra messaggio per l'utente
                btn.innerHTML = '<span class="spinner"></span> Stopping...';
                btn.disabled = true;
                
                // Aspetta un po' e poi ricarica
                setTimeout(() => {
                    showToast('Reloading to check status...', 'info');
                    location.reload();
                }, 3000);
            } else {
                showToast(`Error: ${fetchError.message}`, 'error');
                btn.disabled = false;
                btn.innerHTML = originalHTML;
            }
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
        // Trova il bottone di nuovo in caso di errore generale
        const card = document.querySelector(`[data-name="${imageName}"]`);
        if (card) {
            const btn = card.querySelector('.btn-danger');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<span class="btn-icon">⏹</span> Stop';
            }
        }
    } finally {
        hideLoader();
    }
}

// Poll container status after stop
async function pollContainerStopStatus(imageName, containerName, btn) {
    let attempts = 0;
    const maxAttempts = 60;
    
    //console.log('pollContainerStopStatus: Starting for', { containerName, imageName, startTime: new Date().toISOString() });
    
    const poll = async () => {
        //console.log('pollContainerStopStatus: Attempt', attempts + 1, 'of', maxAttempts, 'for', containerName);
        try {
            const controller = new AbortController();
            const startTime = Date.now();
            //console.log('pollContainerStopStatus: Fetching / for status check');
            const timeoutId = setTimeout(() => {
                //console.log('pollContainerStopStatus: Timeout for attempt', attempts + 1, 'after 10s');
                controller.abort();
            }, 10000);
            
            const response = await fetch('/', { signal: controller.signal });
            //console.log('pollContainerStopStatus: Fetch / response:', response.status, 'after', (Date.now() - startTime) / 1000 + 's');
            clearTimeout(timeoutId);
            
            const text = await response.text();
            //console.log('pollContainerStopStatus: Received response, text length:', text.length);
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');
            const newCard = doc.querySelector(`[data-name="${imageName}"]`);
            
            if (newCard) {
                const statusText = newCard.querySelector('.status-text').textContent.toLowerCase();
                //console.log('pollContainerStopStatus: Status for', imageName, ':', statusText);
                if (statusText === 'stopped') {
                    showToast(`Container ${containerName} stopped successfully`, 'success');
                    //console.log('pollContainerStopStatus: Stop confirmed, reloading');
                    location.reload();
                    return;
                }
            } else {
                //console.log('pollContainerStopStatus: Card not found for', imageName);
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                //console.log('pollContainerStopStatus: Scheduling next poll in 1-1.5s');
                await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 500));
                poll();
            } else {
                showToast(`Container may still be stopping - refresh page to check`, 'warning');
                //console.log('pollContainerStopStatus: Max attempts reached', maxAttempts);
                btn.disabled = false;
                btn.innerHTML = '<span class="btn-icon">⏹</span> Stop';
            }
        } catch (e) {
            console.error('pollContainerStopStatus: Error in attempt', attempts + 1, ':', e);
            if (e.name === 'AbortError') {
                showToast('Polling timeout - retrying...', 'warning');
                //console.log('pollContainerStopStatus: Polling timeout for', containerName);
            }
            attempts++;
            if (attempts < maxAttempts) {
                //console.log('pollContainerStopStatus: Retrying after error in 1-1.5s');
                await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 500));
                poll();
            } else {
                showToast('Polling failed - refresh manually', 'error');
                //console.log('pollContainerStopStatus: Polling failed after', maxAttempts, 'attempts');
            }
        }
    };
    
    poll();
}

// Show Logs
async function showLogs(container) {
    try {
        const response = await fetch(`/logs/${container}`);
        const data = await response.json();

        document.getElementById('logContainerName').textContent = container;
        document.getElementById('logContent').textContent = data.logs || 'No logs available';
        openModal('logModal');
    } catch (e) {
        showToast(`Error loading logs: ${e.message}`, 'error');
    }
}

// Modal Management
function openModal(modalId) {
    document.getElementById(modalId).classList.add('modal-open');
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('modal-open');
    document.body.style.overflow = '';
}

// Console Management
function openConsole(container, imageName) {
    document.getElementById('consoleContainerName').textContent = container;
    document.getElementById('consoleStatus').textContent = '● Connecting...';
    openModal('consoleModal');

    if (term) {
        term.dispose();
        term = null;
    }

    term = new Terminal({
        cursorBlink: true,
        theme: {
            background: '#1e1e1e',
            foreground: '#d4d4d4',
            cursor: '#ffffff',
            selection: '#264f78'
        },
        fontSize: 14,
        fontFamily: '"Cascadia Code", "Fira Code", "Consolas", "Monaco", monospace',
        scrollback: 10000,
        allowTransparency: true
    });

    fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);

    try {
        webglAddon = new WebglAddon.WebglAddon(); // Store reference to WebGL addon
        term.loadAddon(webglAddon);
    } catch (e) {
        console.warn('WebGL addon not available, using canvas renderer');
    }

    term.open(document.getElementById('terminal'));
    fitAddon.fit();
    term.focus();

    window.addEventListener('resize', () => {
        if (fitAddon) fitAddon.fit();
    });

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/console/${container}`);

    ws.onopen = () => {
        //console.log('WebSocket connected');
        document.getElementById('consoleStatus').textContent = '● Connected';
        document.getElementById('consoleStatus').className = 'console-status console-connected';
        term.write('\r\n\x1b[32m✓ Connected to console\x1b[0m\r\n\r\n');
    };

    ws.onmessage = (event) => {
        term.write(event.data);
        term.scrollToBottom();
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        document.getElementById('consoleStatus').textContent = '● Error';
        document.getElementById('consoleStatus').className = 'console-status console-error';
        term.write('\r\n\x1b[31m✗ Connection error\x1b[0m\r\n');
    };

    ws.onclose = () => {
        //console.log('WebSocket closed');
        document.getElementById('consoleStatus').textContent = '● Disconnected';
        document.getElementById('consoleStatus').className = 'console-status console-disconnected';

        // Only write to terminal if it still exists
        if (term) {
            term.write('\r\n\x1b[33m⚠ Console disconnected\x1b[0m\r\n');
        }
    };

    term.onData(data => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(data);
        }
    });
}

function closeConsole() {
    // Close WebSocket first, before disposing terminal
    if (ws) {
        ws.onclose = null; // Remove the onclose handler to prevent it from trying to write to disposed terminal
        ws.close();
        ws = null;
    }

    if (term) {
        // Dispose WebGL addon first, if it exists
        if (webglAddon) {
            try {
                webglAddon.dispose();
            } catch (e) {
                console.warn('Error disposing WebGL addon:', e);
            }
            webglAddon = null;
        }
        term.dispose();
        term = null;
    }

    fitAddon = null;
    closeModal('consoleModal');
}

// Event Listeners
filterInput.addEventListener('input', applyFilters);
categoryFilter.addEventListener('change', () => applyFilters());
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (document.getElementById('consoleModal').classList.contains('modal-open')) {
            closeConsole();
        } else if (document.getElementById('logModal').classList.contains('modal-open')) {
            closeModal('logModal');
        }
    }
    if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        filterInput.focus();
    }
});

// Initialize
applyFilters();
