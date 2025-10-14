let operationInProgress = false;
let systemInfoInterval = null;

// Modal Management
function openModal(modalId) {
    document.getElementById(modalId).classList.add('modal-open');
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('modal-open');
    document.body.style.overflow = '';
}

// Toast system
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = { success: '✓', error: '✗', info: 'ℹ', warning: '⚠' };
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

/**
 * Generic polling function for operation status
 * @param {string} operationId - Operation ID to poll
 * @param {string} operationType - Type of operation (stop, restart, cleanup)
 * @param {number} maxAttempts - Maximum polling attempts
 */
async function pollOperationStatus(operationId, operationType, maxAttempts = 180) {
    let attempts = 0;
    
    const operationLabels = {
        'stop': { verb: 'Stopping', field: 'stopped', emoji: '⏹' },
        'restart': { verb: 'Restarting', field: 'restarted', emoji: '🔄' },
        'cleanup': { verb: 'Cleaning up', field: 'removed', emoji: '🧹' }
    };
    
    const config = operationLabels[operationType] || operationLabels['stop'];
    
    // Variable to track total
    let totalContainers = '?';
    
    const poll = async () => {
        try {
            const response = await fetch(`/api/operation-status/${operationId}`);
            const statusData = await response.json();

            // Update total when available
            if (statusData.total !== undefined) {
                totalContainers = statusData.total;
            }
            
            const completed = statusData[config.field] || 0;
            const remaining = totalContainers !== '?' ? totalContainers - completed : '?';
            
            // Always show progress, even if 0 of X
            showLoader(`${config.verb} containers: ${completed} of ${totalContainers} completed (${remaining} remaining)`);

            if (statusData.status === 'completed') {
                showToast(`${config.emoji} Successfully ${operationType === 'stop' ? 'stopped' : operationType === 'restart' ? 'restarted' : 'cleaned up'} ${completed} containers! Reloading page...`, 'success');
                hideLoader();
                
                // Wait for user to see toast, then reload
                setTimeout(() => {
                    location.reload(); 
                }, 2500);
                return;
            }

            if (statusData.status === 'error') {
                showToast(`❌ ${config.verb} operation failed: ${statusData.error}`, 'error');
                hideLoader();
                resumeSystemInfoUpdates();
                return;
            }
            
            // Continue polling
            attempts++;
            if (attempts < maxAttempts) {
                // Poll every 1 second
                setTimeout(poll, 1000); 
            } else {
                showToast(`⏰ Operation timed out after ${maxAttempts} seconds. Please check the page or refresh manually.`, 'warning');
                hideLoader();
                resumeSystemInfoUpdates();
            }

        } catch (e) {
            console.error('Polling error:', e);
            showToast('❌ An error occurred during status check.', 'error');
            hideLoader();
            resumeSystemInfoUpdates();
        }
    };

    // Show loader immediately with initial state
    showLoader(`${config.verb} containers: 0 of ${totalContainers} completed...`);
    
    // Start the polling
    poll();
}

// Show Server Logs in Modal
async function showServerLogs() {
    try {
        showLoader('Loading server logs...');
        const response = await fetch('/api/logs');
        const logs = await response.text();
        document.getElementById('logContent').textContent = logs || 'No logs available';
        openModal('logModal');
    } catch (e) {
        showToast(`Error loading logs: ${e.message}`, 'error');
    } finally {
        hideLoader();
    }
}

// Show Backups in Modal
async function showBackups() {
    try {
        showLoader('Loading backups...');
        const response = await fetch('/api/backups');
        const data = await response.json();
        const list = document.getElementById('backupsList');
        if (data.backups.length === 0) {
            list.innerHTML = '<p style="color: #64748b;">No backups found</p>';
        } else {
            let html = '<table class="backups-table"><thead><tr><th>Category</th><th>File</th><th>Size</th><th>Modified</th><th>Actions</th></tr></thead><tbody>';
            data.backups.forEach(backup => {
                const date = new Date(backup.modified * 1000).toLocaleString();
                let size;
                if (backup.size >= 1024 * 1024) {
                    size = (backup.size / (1024 * 1024)).toFixed(2) + ' MB';
                } else if (backup.size >= 1024) {
                    size = (backup.size / 1024).toFixed(2) + ' KB';
                } else {
                    size = backup.size + ' bytes';
                }
                html += `<tr>
                    <td>${backup.category}</td>
                    <td>${backup.file}</td>
                    <td>${size}</td>
                    <td>${date}</td>
                    <td><button class="btn btn-primary btn-sm" onclick="downloadBackup('${backup.category}', '${backup.file}')">Download</button></td>
                </tr>`;
            });
            html += '</tbody></table>';
            list.innerHTML = html;
        }
        openModal('backupsModal');
    } catch (e) {
        showToast(`Error loading backups: ${e.message}`, 'error');
    } finally {
        hideLoader();
    }
}

// Download Backup
function downloadBackup(category, filename) {
    const url = `/api/download-backup/${encodeURIComponent(category)}/${encodeURIComponent(filename)}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast(`Downloading ${filename}...`, 'info');
}

// Pause and resume interval
function pauseSystemInfoUpdates() {
    operationInProgress = true;
    if (systemInfoInterval) {
        clearInterval(systemInfoInterval);
        systemInfoInterval = null;
    }
}

function resumeSystemInfoUpdates() {
    operationInProgress = false;
    if (!systemInfoInterval) {
        systemInfoInterval = setInterval(loadSystemInfo, 30000);
    }
    loadSystemInfo();
}

// Stop all containers - UNIFIED VERSION
async function stopAll() {
    try {
        const confirmed = await showConfirmModal(
            'Stop All Containers',
            'Are you sure you want to stop ALL running containers? This will gracefully stop all running playground containers.',
            'danger'
        );
        if (!confirmed) {
            return;
        }

        pauseSystemInfoUpdates();
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
                // pollOperationStatus will handle the loader
                pollOperationStatus(data.operation_id, 'stop');
            } else {
                showToast(`Failed to start stop operation: ${data.error || response.statusText}`, 'error');
                hideLoader();
                resumeSystemInfoUpdates();
            }
        } catch (fetchError) {
            clearTimeout(timeoutId);
            if (fetchError.name === 'AbortError') {
                showToast('Operation request timed out - please check server status', 'warning');
            } else {
                showToast(`Error: ${fetchError.message}`, 'error');
            }
            hideLoader();
            resumeSystemInfoUpdates();
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
        hideLoader();
        resumeSystemInfoUpdates();
    }
}

// Restart all containers - UNIFIED VERSION
async function restartAll() {
    try {
        const confirmed = await showConfirmModal(
            'Restart All Containers',
            'Are you sure you want to restart ALL running containers? This will restart all containers one by one.',
            'warning'
        );
        if (!confirmed) return;

        pauseSystemInfoUpdates();
        showToast('Initiating restart all operation...', 'info');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);

        try {
            const response = await fetch('/api/restart-all', { 
                method: 'POST',
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (response.ok) {
                // pollOperationStatus will handle the loader
                pollOperationStatus(data.operation_id, 'restart');
            } else {
                showToast(`Failed to start restart operation: ${data.error || response.statusText}`, 'error');
                hideLoader();
                resumeSystemInfoUpdates();
            }

        } catch (fetchError) {
            clearTimeout(timeoutId);
            
            if (fetchError.name === 'AbortError') {
                showToast('⏰ Operation request timed out - please check server status', 'warning');
            } else {
                showToast(`❌ Error: ${fetchError.message}`, 'error');
            }
            hideLoader();
            resumeSystemInfoUpdates();
        }
    } catch (e) {
        showToast(`❌ Error: ${e.message}`, 'error');
        hideLoader();
        resumeSystemInfoUpdates();
    }
}

// Cleanup all - UNIFIED VERSION
async function cleanupAll() {
    try {
        const confirmed = await showConfirmModal(
            'Cleanup All Containers',
            '⚠️ DANGER: This will STOP and REMOVE ALL playground containers! Are you absolutely sure?',
            'danger'
        );
        if (!confirmed) return;

        const doubleCheck = await showConfirmModal(
            'Final Confirmation',
            'This action cannot be undone. Are you sure you want to proceed?',
            'danger'
        );
        if (!doubleCheck) return;

        pauseSystemInfoUpdates();
        showToast('Initiating cleanup all operation...', 'warning');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);

        try {
            const response = await fetch('/api/cleanup-all', { 
                method: 'POST',
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (response.ok) {
                // pollOperationStatus will handle the loader
                pollOperationStatus(data.operation_id, 'cleanup');
            } else {
                showToast(`Failed to start cleanup operation: ${data.error || response.statusText}`, 'error');
                hideLoader();
                resumeSystemInfoUpdates();
            }

        } catch (fetchError) {
            clearTimeout(timeoutId);
            
            if (fetchError.name === 'AbortError') {
                showToast('⏰ Operation request timed out - please check server status', 'warning');
            } else {
                showToast(`❌ Error: ${fetchError.message}`, 'error');
            }
            hideLoader();
            resumeSystemInfoUpdates();
        }
    } catch (e) {
        showToast(`❌ Error: ${e.message}`, 'error');
        hideLoader();
        resumeSystemInfoUpdates();
    }
}

// Start category
async function startCategory(category) {
    try {
        const confirmed = await showConfirmModal(
            'Start Category',
            `Are you sure you want to start all containers in category: ${category}?`,
            'success'
        );
        if (!confirmed) return;

        pauseSystemInfoUpdates();
        showLoader(`Starting containers in category ${category}...`);
        showToast(`Starting ${category} containers...`, 'info');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000);

        try {
            const response = await fetch(`/api/start-category/${category}`, { 
                method: 'POST',
                signal: controller.signal,
                keepalive: false
            });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (response.ok) {
                showToast(`Successfully started ${data.started} containers`, 'success');
                hideLoader();
                setTimeout(() => location.reload(), 2000);
            } else {
                showToast('Failed to start category', 'error');
                hideLoader();
                resumeSystemInfoUpdates();
            }
        } catch (fetchError) {
            clearTimeout(timeoutId);
            
            if (fetchError.name === 'AbortError') {
                showToast('Operation timeout - please wait and refresh manually', 'warning');
                hideLoader();
                setTimeout(() => location.reload(), 5000);
            } else {
                showToast(`Error: ${fetchError.message}`, 'error');
                hideLoader();
                resumeSystemInfoUpdates();
            }
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
        hideLoader();
        resumeSystemInfoUpdates();
    }
}

// Start by category
async function startByCategory() {
    try {
        const category = await showInputModal(
            'Start Category',
            'Enter the category name to start all its containers:',
            'e.g., linux, database, programming...'
        );
        if (!category) return;

        pauseSystemInfoUpdates();
        showLoader(`Starting containers in category ${category}...`);
        showToast(`Starting all containers in category: ${category}...`, 'info');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000);

        try {
            const response = await fetch(`/api/start-category/${category}`, { 
                method: 'POST',
                signal: controller.signal,
                keepalive: false
            });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (response.ok) {
                if (data.started > 0) {
                    showToast(`Successfully started ${data.started} containers in ${category}`, 'success');
                } else {
                    showToast(`No containers found in category: ${category}`, 'warning');
                }
                hideLoader();
                setTimeout(() => location.reload(), 2000);
            } else {
                showToast(data.detail || 'Failed to start category', 'error');
                hideLoader();
                resumeSystemInfoUpdates();
            }
        } catch (fetchError) {
            clearTimeout(timeoutId);
            
            if (fetchError.name === 'AbortError') {
                showToast('Operation timeout - please wait and refresh manually', 'warning');
                hideLoader();
                setTimeout(() => location.reload(), 5000);
            } else {
                showToast(`Error: ${fetchError.message}`, 'error');
                hideLoader();
                resumeSystemInfoUpdates();
            }
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
        hideLoader();
        resumeSystemInfoUpdates();
    }
}

// View category
function viewCategory(category) {
    window.location.href = `/?category=${category}`;
}

// Export configuration
async function exportConfig() {
    showToast('Exporting configuration...', 'info');
    
    try {
        const response = await fetch('/api/export-config');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `playground-config-${new Date().toISOString().split('T')[0]}.yml`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showToast('Configuration exported', 'success');
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// Load system info - WITH DEBOUNCING
let loadSystemInfoDebounceTimer = null;
async function loadSystemInfo() {
    // Debounce
    if (loadSystemInfoDebounceTimer) {
        return;
    }
    
    loadSystemInfoDebounceTimer = setTimeout(() => {
        loadSystemInfoDebounceTimer = null;
    }, 2000);
    
    if (operationInProgress) {
        return;
    }
    
    try {
        const startTime = Date.now();
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch('/api/system-info', { signal: controller.signal });
        clearTimeout(timeoutId);
        
        const data = await response.json();
        
        // Update UI
        const statTotal = document.getElementById('stat-total');
        const statRunning = document.getElementById('stat-running');
        const statStopped = document.getElementById('stat-stopped');
        
        if (statTotal) statTotal.textContent = data.counts.total;
        if (statRunning) statRunning.textContent = data.counts.running;
        if (statStopped) statStopped.textContent = data.counts.stopped;
        
        document.getElementById('docker-info').textContent = 
            `Version: ${data.docker.version}\nContainers: ${data.docker.containers}\nImages: ${data.docker.images}`;
        
        document.getElementById('network-info').textContent = 
            `Name: ${data.network.name}\nDriver: ${data.network.driver}\nSubnet: ${data.network.subnet || 'N/A'}`;
        
        document.getElementById('volume-info').textContent = 
            `Path: ${data.volume.path}\nSize: ${data.volume.size || 'N/A'}`;
        
        const activeList = document.getElementById('active-list');
        if (data.active_containers.length === 0) {
            activeList.innerHTML = '<p style="color: #64748b;">No active containers</p>';
        } else {
            activeList.innerHTML = data.active_containers.map(c => 
                `<div class="active-container-item">
                    <span>🐳 ${c.name}</span>
                    <span class="container-status">${c.status}</span>
                </div>`
            ).join('');
        }
    } catch (e) {
        if (e.name === 'AbortError') {
            console.error('loadSystemInfo: Timeout after 5s');
        } else {
            console.error('loadSystemInfo: Failed:', e);
        }
    }
}

let isInitialized = false;

function initializeSystemInfo() {
    if (isInitialized) {
        return;
    }
    
    isInitialized = true;
    
    loadSystemInfo();
    
    if (systemInfoInterval) {
        clearInterval(systemInfoInterval);
    }
    
    systemInfoInterval = setInterval(loadSystemInfo, 30000);
}

// Load on page ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSystemInfo);
} else {
    initializeSystemInfo();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (systemInfoInterval) {
        clearInterval(systemInfoInterval);
        systemInfoInterval = null;
    }
});

// Start group from manage page
async function startGroupFromManage(groupName) {
    try {
        const confirmed = await showConfirmModal(
            'Start Application Stack',
            `Start all containers in <strong>${groupName}</strong>?`,
            'success'
        );
        if (!confirmed) return;

        pauseSystemInfoUpdates();
        showLoader(`Initiating start for '${groupName}'...`);
        showToast(`Starting ${groupName}...`, 'info');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        const response = await fetch(`/api/start-group/${encodeURIComponent(groupName)}`, { 
            method: 'POST',
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        const data = await response.json();

        if (response.ok) {
            // Use the same polling function from app.js
            pollStartGroupStatusManager(data.operation_id, groupName);
        } else {
            showToast(data.detail || 'Failed to start stack', 'error');
            hideLoader();
            resumeSystemInfoUpdates();
        }
    } catch (e) {
        if (e.name === 'AbortError') {
            showToast('Request timed out', 'warning');
        } else {
            showToast(`Error: ${e.message}`, 'error');
        }
        hideLoader();
        resumeSystemInfoUpdates();
    }
}

/**
 * Poll start group status from manager page
 */
async function pollStartGroupStatusManager(operationId, groupName) {
    const maxAttempts = 180;
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
            
            showLoader(
                `Starting '${groupName}': ${completed}/${total} | ` +
                `✓ ${started}, ⚡ ${alreadyRunning}, ✗ ${failed}`
            );

            if (statusData.status === 'completed') {
                let message = `Stack '${groupName}': `;
                let details = [];
                if (started > 0) details.push(`${started} started`);
                if (alreadyRunning > 0) details.push(`${alreadyRunning} running`);
                if (failed > 0) details.push(`${failed} failed`);
                
                message += details.join(', ');
                
                // Mostra errori dettagliati se presenti
                if (statusData.errors && statusData.errors.length > 0) {
                    showErrorsAsToasts(statusData.errors, message, failed > 0 ? 'warning' : 'success');
                } else {
                    showToast(message, failed > 0 ? 'warning' : 'success');
                }
                
                hideLoader();
                resumeSystemInfoUpdates();
                return;
            }

            if (statusData.status === 'error') {
                const errorMessage = statusData.error || 'Unknown error occurred';
                showToast(`Start failed: ${errorMessage}`, 'error');
                hideLoader();
                resumeSystemInfoUpdates();
                return;
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 1000);
            } else {
                showToast('Operation timed out. Check status manually.', 'warning');
                hideLoader();
                resumeSystemInfoUpdates();
            }

        } catch (e) {
            console.error('Polling error:', e);
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 1000);
            } else {
                showToast('Polling failed', 'error');
                hideLoader();
                resumeSystemInfoUpdates();
            }
        }
    };

    poll();
}

/**
 * Show errors as sequential toast messages
 */
function showErrorsAsToasts(errors, baseMessage, baseType = 'warning') {
    if (!errors || errors.length === 0) return;
    
    // First show the base message
    showToast(baseMessage, baseType);
    
    // Then show each error as separate toast after a short delay
    errors.forEach((error, index) => {
        setTimeout(() => {
            showToast(`Error: ${error}`, 'error');
        }, (index + 1) * 800); // 800ms delay between toasts
    });
}

// Stop group from manage page
async function stopGroupFromManage(groupName) {
    try {
        const confirmed = await showConfirmModal(
            'Stop Application Stack',
            `Stop all containers in <strong>${groupName}</strong>?`,
            'warning'
        );
        if (!confirmed) return;

        pauseSystemInfoUpdates();
        showLoader(`Initiating stop for '${groupName}'...`);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        const response = await fetch(`/api/stop-group/${encodeURIComponent(groupName)}`, { 
            method: 'POST',
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        const data = await response.json();

        if (response.ok) {
            // Start polling
            pollStopGroupStatusManager(data.operation_id, groupName);
        } else {
            showToast(data.detail || 'Failed to stop stack', 'error');
            hideLoader();
            resumeSystemInfoUpdates();
        }
    } catch (e) {
        if (e.name === 'AbortError') {
            showToast('Request timed out', 'warning');
        } else {
            showToast(`Error: ${e.message}`, 'error');
        }
        hideLoader();
        resumeSystemInfoUpdates();
    }
}

/**
 * Poll stop group status from manager page
 */
async function pollStopGroupStatusManager(operationId, groupName) {
    const maxAttempts = 180;
    let attempts = 0;

    const poll = async () => {
        try {
            const response = await fetch(`/api/operation-status/${operationId}`);
            const statusData = await response.json();

            // Default values to handle incomplete status data
            const total = statusData.total || 0;
            const stopped = statusData.stopped || 0;
            const notRunning = statusData.not_running || 0;
            const failed = statusData.failed || 0;
            const completed = stopped + notRunning + failed;
            
            showLoader(
                `Stopping '${groupName}': ${completed}/${total} | ` +
                `⏹ ${stopped}, ⏸ ${notRunning}, ✗ ${failed}`
            );

            if (statusData.status === 'completed') {
                let message = `Stack '${groupName}': `;
                let details = [];
                if (stopped > 0) details.push(`${stopped} stopped`);
                if (notRunning > 0) details.push(`${notRunning} not running`);
                if (failed > 0) details.push(`${failed} failed`);
                
                if (details.length > 0) {
                    message += details.join(', ');
                }
                
                showToast(message, failed > 0 ? 'warning' : 'success');
                hideLoader();
                resumeSystemInfoUpdates();
                return;
            }

            if (statusData.status === 'error') {
                showToast(`Stop failed: ${statusData.error || 'Unknown error'}`, 'error');
                hideLoader();
                resumeSystemInfoUpdates();
                return;
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 1000);
            } else {
                showToast('Operation timed out. Check status manually.', 'warning');
                hideLoader();
                resumeSystemInfoUpdates();
            }

        } catch (e) {
            console.error('Polling error:', e);
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 1000);
            } else {
                showToast('Polling failed', 'error');
                hideLoader();
                resumeSystemInfoUpdates();
            }
        }
    };

    poll();
}

// View group - redirect to main page with group filter
function viewGroup(groupName) {
    window.location.href = `/?group=${encodeURIComponent(groupName)}`;
}
