let ws = null;
let term = null;
let fitAddon = null;
let webglAddon = null;

// =========================================================
// Helper Functions (Toast, Loader, Confirm Modal)
// =========================================================

// Toast Notification System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) {
        console.warn('Toast container is missing. Message:', message);
        return;
    }
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

// =========================================================
// Polling Logic for Stop All Containers (CORRECTED)
// =========================================================

/**
 * Polls the operation status endpoint until the 'stop all' task is complete.
 * @param {string} operationId The ID of the background operation.
 */
async function pollStopAllStatus(operationId) {
    const maxAttempts = 60; // Max 60 seconds of polling
    let attempts = 0;

    showLoader('Stopping containers: Awaiting progress...');

    const poll = async () => {
        try {
            const response = await fetch(`/api/operation-status/${operationId}`);
            const statusData = await response.json();

            // Update loader with current progress
            const total = statusData.total || '?';
            const stopped = statusData.stopped || 0;
            showLoader(`Stopping containers: ${stopped} of ${total} | Status: ${statusData.status}`);

            if (statusData.status === 'completed') {
                showToast(`Stopped ${stopped} containers successfully!`, 'success');
                hideLoader();

                // Aspetta che l'utente veda il toast, POI ricarica
                setTimeout(() => {
                    location.reload();
                }, 2500); // 2.5 secondi per vedere il toast
                return;
            }

            if (statusData.status === 'error') {
                showToast(`Stop operation failed: ${statusData.error}`, 'error');
                hideLoader();
                return;
            }

            // Continue polling
            attempts++;
            if (attempts < maxAttempts) {
                // Poll every 1000ms (1 second)
                setTimeout(poll, 1000);
            } else {
                showToast(`Operation timed out after ${maxAttempts} attempts. Please check the 'Manage' page or refresh manually.`, 'warning');
                hideLoader();
            }

        } catch (e) {
            console.error('Polling error:', e);
            showToast('An error occurred during status check.', 'error');
            hideLoader();
        }
    };

    // Start the polling
    poll();
}

// =========================================================
// Main Functions
// =========================================================

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

// Stop all running containers (FINAL CORRECTED LOGIC)
async function stopAllRunning() {
    try {
        const confirmed = await showConfirmModal(
            'Stop All Containers',
            'Are you sure you want to stop ALL running containers? This will gracefully stop all running playground containers.',
            'danger'
        );
        if (!confirmed) {
            return;
        }

        showLoader('Initiating stop all operation...');
        showToast('Initiating stop all operation...', 'info');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
        }, 120000); // 120s timeout for initial request

        try {
            const response = await fetch('/api/stop-all', {
                method: 'POST',
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (response.ok) {
                // *** FIX IS HERE: CALL THE POLLING FUNCTION ***
                showToast(`Stop operation started. ID: ${data.operation_id}`, 'info');
                pollStopAllStatus(data.operation_id);
            } else {
                showToast(`Failed to start stop operation: ${data.error || response.statusText}`, 'error');
                hideLoader();
            }
        } catch (fetchError) {
            clearTimeout(timeoutId);
            if (fetchError.name === 'AbortError') {
                showToast('Operation request timed out - please check server status', 'warning');
            } else {
                showToast(`Error: ${fetchError.message}`, 'error');
            }
            hideLoader();
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
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
            `Are you sure you want to stop container <strong>${containerName}</strong>? Any unsaved data might be lost.`,
            'warning'
        );
        if (!confirmed) return;

        const card = document.querySelector(`[data-name="${imageName}"]`);
        const btn = card.querySelector('.btn-danger');
        const originalHTML = btn.innerHTML;

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Stopping...';

        showLoader(`Stopping container ${containerName}...`);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes

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
                btn.innerHTML = '<span class="spinner"></span> Stopping...';
                btn.disabled = true;

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

    const poll = async () => {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => {
                controller.abort();
            }, 10000);

            const response = await fetch('/', { signal: controller.signal });
            clearTimeout(timeoutId);

            const text = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');
            const newCard = doc.querySelector(`[data-name="${imageName}"]`);

            if (newCard) {
                const statusText = newCard.querySelector('.status-text').textContent.toLowerCase();
                if (statusText === 'stopped') {
                    showToast(`Container ${containerName} stopped successfully`, 'success');
                    location.reload();
                    return;
                }
            }

            attempts++;
            if (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 500));
                poll();
            } else {
                showToast(`Container may still be stopping - refresh page to check`, 'warning');
                btn.disabled = false;
                btn.innerHTML = '<span class="btn-icon">⏹</span> Stop';
            }
        } catch (e) {
            console.error('pollContainerStopStatus: Error in attempt', attempts + 1, ':', e);
            if (e.name === 'AbortError') {
                showToast('Polling timeout - retrying...', 'warning');
            }
            attempts++;
            if (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 500));
                poll();
            } else {
                showToast('Polling failed - refresh manually', 'error');
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
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('modal-open');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('modal-open');
        document.body.style.overflow = '';
    }
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
        webglAddon = new WebglAddon.WebglAddon();
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
        document.getElementById('consoleStatus').textContent = '● Disconnected';
        document.getElementById('consoleStatus').className = 'console-status console-disconnected';

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
    if (ws) {
        ws.onclose = null;
        ws.close();
        ws = null;
    }

    if (term) {
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
if (filterInput) filterInput.addEventListener('input', applyFilters);
if (categoryFilter) categoryFilter.addEventListener('change', () => applyFilters());
document.addEventListener('keydown', (e) => {
    // Optional chaining to prevent errors if elements are null
    if (e.key === 'Escape') {
        if (document.getElementById('consoleModal')?.classList.contains('modal-open')) {
            closeConsole();
        } else if (document.getElementById('logModal')?.classList.contains('modal-open')) {
            closeModal('logModal');
        }
    }
    if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        if (filterInput) filterInput.focus();
    }
});

async function startGroup(groupName) {
    const button = event.target;
    const originalText = button.textContent;
    
    button.textContent = '🔄 Starting...';
    button.disabled = true;
    
    try {
        showLoader(`Initiating start for group '${groupName}'...`);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s for initial request
        
        const response = await fetch(`/api/start-group/${encodeURIComponent(groupName)}`, {
            method: 'POST',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Starting group '${groupName}'...`, 'info');
            // Start polling for status
            pollStartGroupStatus(data.operation_id, groupName);
        } else {
            showToast(`Error: ${data.detail || 'Failed to start group'}`, 'error');
            hideLoader();
            button.textContent = originalText;
            button.disabled = false;
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            showToast('Request timed out', 'warning');
        } else {
            showToast('Error starting group', 'error');
            console.error('Error starting group:', error);
        }
        hideLoader();
        button.textContent = originalText;
        button.disabled = false;
    }
}

/**
 * Poll the status of a start group operation
 */
async function pollStartGroupStatus(operationId, groupName) {
    const maxAttempts = 180; // 3 minutes max
    let attempts = 0;

    const poll = async () => {
        try {
            const response = await fetch(`/api/operation-status/${operationId}`);
            const statusData = await response.json();

            const total = statusData.total || '?';
            const started = statusData.started || 0;
            const alreadyRunning = statusData.already_running || 0;
            const failed = statusData.failed || 0;
            const completed = started + alreadyRunning + failed;
            const remaining = total !== '?' ? total - completed : '?';
            
            // Update loader with detailed progress
            showLoader(
                `Starting '${groupName}': ${completed}/${total} | ` +
                `✓ ${started} started, ` +
                `⚡ ${alreadyRunning} running, ` +
                `✗ ${failed} failed, ` +
                `⏳ ${remaining} remaining`
            );

            if (statusData.status === 'completed') {
                hideLoader();
                
                // Build success message
                let message = `Group '${groupName}' started! `;
                let details = [];
                if (started > 0) details.push(`${started} started`);
                if (alreadyRunning > 0) details.push(`${alreadyRunning} already running`);
                if (failed > 0) details.push(`${failed} failed`);
                message += details.join(', ');
                
                // Show appropriate toast
                if (failed > 0) {
                    showToast(message, 'warning');
                    console.warn('Start group errors:', statusData.errors);
                } else {
                    showToast(message, 'success');
                }
                
                // Reload page after delay
                setTimeout(() => {
                    location.reload();
                }, 2000);
                return;
            }

            if (statusData.status === 'error') {
                showToast(`Start group failed: ${statusData.error}`, 'error');
                hideLoader();
                return;
            }
            
            // Continue polling
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 1000); // Poll every second
            } else {
                showToast(`Operation timed out after ${maxAttempts} seconds. Check status manually.`, 'warning');
                hideLoader();
            }

        } catch (e) {
            console.error('Polling error:', e);
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 1000);
            } else {
                showToast('Polling failed. Please refresh the page.', 'error');
                hideLoader();
            }
        }
    };

    // Start polling
    poll();
}

/**
 * Poll the status of a stop group operation
 */
async function pollStopGroupStatus(operationId, groupName) {
    const maxAttempts = 180;
    let attempts = 0;

    const poll = async () => {
        try {
            const response = await fetch(`/api/operation-status/${operationId}`);
            const statusData = await response.json();

            // *** FIX: Usa default values se i campi non esistono ***
            const total = statusData.total || 0;
            const stopped = statusData.stopped || 0;
            const notRunning = statusData.not_running || 0;
            const failed = statusData.failed || 0;
            const completed = stopped + notRunning + failed;
            const remaining = total > 0 ? total - completed : 0;
            
            showLoader(
                `Stopping '${groupName}': ${completed}/${total} | ` +
                `⏹ ${stopped} stopped, ` +
                `⏸ ${notRunning} not running, ` +
                `✗ ${failed} failed, ` +
                `⏳ ${remaining} remaining`
            );

            if (statusData.status === 'completed') {
                let message = `Group '${groupName}' stopped! `;
                let details = [];
                if (stopped > 0) details.push(`${stopped} stopped`);
                if (notRunning > 0) details.push(`${notRunning} were not running`);
                if (failed > 0) details.push(`${failed} failed`);
                
                if (details.length > 0) {
                    message += details.join(', ');
                } else {
                    message = `Group '${groupName}' operation completed`;
                }
                
                showToast(message, failed > 0 ? 'warning' : 'success');
                hideLoader();
                
                setTimeout(() => {
                    location.reload();
                }, 2000);
                return;
            }

            if (statusData.status === 'error') {
                showToast(`Stop group failed: ${statusData.error || 'Unknown error'}`, 'error');
                hideLoader();
                return;
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 1000);
            } else {
                showToast('Operation timed out. Check status manually.', 'warning');
                hideLoader();
            }

        } catch (e) {
            console.error('Polling error:', e);
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 1000);
            } else {
                showToast('Polling failed. Please refresh the page.', 'error');
                hideLoader();
            }
        }
    };

    poll();
}

// Nuova funzione per stop group
async function stopGroup(groupName) {
    try {
        const confirmed = await showConfirmModal(
            'Stop Group',
            `Are you sure you want to stop all containers in group '<strong>${groupName}</strong>'?`,
            'warning'
        );
        
        if (!confirmed) return;
        
        showLoader(`Initiating stop for group '${groupName}'...`);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s for initial request
        
        const response = await fetch(`/api/stop-group/${encodeURIComponent(groupName)}`, {
            method: 'POST',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Stopping group '${groupName}'...`, 'info');
            // Start polling for status
            pollStopGroupStatus(data.operation_id, groupName);
        } else {
            showToast(`Error: ${data.detail || 'Failed to stop group'}`, 'error');
            hideLoader();
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            showToast('Request timed out', 'warning');
        } else {
            showToast('Error stopping group', 'error');
            console.error('Error stopping group:', error);
        }
        hideLoader();
    }
}

// Nuova funzione per controllare lo stato del gruppo
async function checkGroupStatus(groupName) {
    try {
        const response = await fetch(`/api/group-status/${groupName}`);
        const result = await response.json();
        
        if (response.ok) {
            console.log('Group status:', result);
            return result;
        }
    } catch (error) {
        console.error('Error checking group status:', error);
    }
    return null;
}

// =========================================================
// Quick Search from Group Container Tags
// =========================================================

/**
 * Filter containers by clicking on container tags in groups
 */
function quickSearchContainer(containerName) {
    // Set the search input
    const filterInput = document.getElementById('filter');
    if (filterInput) {
        filterInput.value = containerName;
        filterInput.focus();
        
        // Trigger the filter
        applyFilters();
        
        // Scroll to the container cards section
        const imageGrid = document.querySelector('.image-grid');
        if (imageGrid) {
            imageGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        // Visual feedback - highlight the matching card briefly
        setTimeout(() => {
            const matchingCard = document.querySelector(`.image-card[data-name="${containerName}"]`);
            if (matchingCard) {
                matchingCard.style.transition = 'all 0.3s ease';
                matchingCard.style.transform = 'scale(1.02)';
                matchingCard.style.boxShadow = '0 8px 30px rgba(102, 126, 234, 0.3)';
                
                setTimeout(() => {
                    matchingCard.style.transform = '';
                    matchingCard.style.boxShadow = '';
                }, 600);
            }
        }, 300);
        
        // Show toast notification
        showToast(`🔍 Filtered to: ${containerName}`, 'info');
    }
}

/**
 * Initialize click handlers for container tags
 */
function initializeContainerTagHandlers() {
    const containerTags = document.querySelectorAll('.container-tag');
    
    containerTags.forEach(tag => {
        const containerName = tag.getAttribute('data-container');
        
        if (containerName) {
            // Add click handler
            tag.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent event bubbling
                quickSearchContainer(containerName);
            });
            
            // Make it visually clear it's clickable
            tag.style.cursor = 'pointer';
            
            // Add hover tooltip
            tag.title = `Click to filter by ${containerName}`;
            
            // Update status dot based on actual container status
            updateContainerTagStatus(tag, containerName);
        }
    });
}

/**
 * Update the status dot color based on container state
 */
function updateContainerTagStatus(tag, containerName) {
    const statusDot = tag.querySelector('.container-status-dot');
    const matchingCard = document.querySelector(`.image-card[data-name="${containerName}"]`);
    
    if (statusDot && matchingCard) {
        const statusText = matchingCard.querySelector('.status-text');
        if (statusText) {
            const isRunning = statusText.textContent.toLowerCase() === 'running';
            
            if (isRunning) {
                statusDot.style.background = '#10b981'; // Green
                statusDot.style.animation = 'pulse 2s ease-in-out infinite';
                tag.setAttribute('data-running', 'true');
            } else {
                statusDot.style.background = '#94a3b8'; // Gray
                statusDot.style.animation = 'none';
                tag.setAttribute('data-running', 'false');
            }
        }
    }
}

/**
 * Refresh all container tag statuses
 */
function refreshContainerTagStatuses() {
    const containerTags = document.querySelectorAll('.container-tag');
    containerTags.forEach(tag => {
        const containerName = tag.getAttribute('data-container');
        if (containerName) {
            updateContainerTagStatus(tag, containerName);
        }
    });
}

function clearSearch() {
    const filterInput = document.getElementById('filter');
    if (filterInput) {
        filterInput.value = '';
        filterInput.focus();
        applyFilters();
        showToast('🔄 Search cleared', 'info');
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeContainerTagHandlers();
        refreshContainerTagStatuses();
    });
} else {
    initializeContainerTagHandlers();
    refreshContainerTagStatuses();
}

// Initialize
applyFilters();