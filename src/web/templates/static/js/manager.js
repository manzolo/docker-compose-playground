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
                // Converti la dimensione in formato leggibile
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

// Pausa e riprendi interval
function pauseSystemInfoUpdates() {
    //console.log('pauseSystemInfoUpdates: Pausing system info updates');
    operationInProgress = true;
    if (systemInfoInterval) {
        clearInterval(systemInfoInterval);
        systemInfoInterval = null;
        //console.log('pauseSystemInfoUpdates: Interval cleared');
    }
}

function resumeSystemInfoUpdates() {
    //console.log('resumeSystemInfoUpdates: Resuming system info updates');
    operationInProgress = false;
    if (!systemInfoInterval) {
        systemInfoInterval = setInterval(loadSystemInfo, 30000);
        //console.log('resumeSystemInfoUpdates: Interval restarted');
    }
    // Refresh immediato
    loadSystemInfo();
}

// Stop all containers
async function stopAll() {
    //console.log('stopAll: Started at', new Date().toISOString());
    try {
        const confirmed = await showConfirmModal(
            'Stop All Containers',
            'Are you sure you want to stop ALL running containers?',
            'danger'
        );
        //console.log('stopAll: User confirmation:', confirmed);
        if (!confirmed) {
            //console.log('stopAll: Cancelled by user');
            return;
        }

        pauseSystemInfoUpdates();
        showLoader('Stopping all containers... This may take several minutes.');
        showToast('Stopping all containers...', 'info');
        //console.log('stopAll: Sending POST to /api/stop-all');

        try {
            // Usa XMLHttpRequest con timeout MOLTO lungo
            const result = await new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                
                // 10 MINUTI di timeout - per Ubuntu che installa pacchetti
                xhr.timeout = 600000;
                
                xhr.ontimeout = () => {
                    //console.log('stopAll: XHR timeout after 10 minutes');
                    reject(new Error('Request timeout after 10 minutes'));
                };
                
                xhr.onerror = () => {
                    //console.log('stopAll: XHR network error');
                    reject(new Error('Network error'));
                };
                
                xhr.onload = () => {
                    //console.log('stopAll: XHR response received, status:', xhr.status);
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const data = JSON.parse(xhr.responseText);
                            //console.log('stopAll: Response data:', data);
                            resolve(data);
                        } catch (parseError) {
                            console.error('stopAll: JSON parse error:', parseError);
                            reject(new Error('Invalid response format'));
                        }
                    } else {
                        //console.log('stopAll: HTTP error status:', xhr.status);
                        reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                    }
                };
                
                xhr.open('POST', '/api/stop-all', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.send();
                //console.log('stopAll: XHR request sent');
            });

            //console.log('stopAll: Success, stopped', result.stopped, 'containers');
            showToast(`Successfully stopped ${result.stopped} containers`, 'success');
            hideLoader();
            
            setTimeout(() => {
                //console.log('stopAll: Reloading page');
                location.reload();
            }, 2000);

        } catch (fetchError) {
            console.error('stopAll: Request failed:', fetchError);
            showToast(`Error: ${fetchError.message}`, 'error');
            hideLoader();
            
            // Mostra un messaggio più utile
            if (fetchError.message.includes('timeout')) {
                showToast('Containers may still be stopping... Reloading in 5s', 'warning');
            }
            
            // Prova a ricaricare comunque dopo un po' per vedere lo stato
            setTimeout(() => {
                showToast('Reloading to check status...', 'info');
                location.reload();
            }, 5000);
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
        console.error('stopAll: General error:', e);
        hideLoader();
        resumeSystemInfoUpdates();
    } finally {
        hideLoader();
    }
}

// Restart all containers
async function restartAll() {
    try {
        const confirmed = await showConfirmModal(
            'Restart All Containers',
            'Are you sure you want to restart ALL running containers?',
            'warning'
        );
        if (!confirmed) return;

        pauseSystemInfoUpdates();
        showLoader('Restarting all containers... This may take a while.');
        showToast('Restarting all containers...', 'info');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000);

        try {
            const response = await fetch('/api/restart-all', { 
                method: 'POST',
                signal: controller.signal,
                keepalive: false
            });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (response.ok) {
                showToast(`Successfully restarted ${data.restarted} containers`, 'success');
                hideLoader();
                setTimeout(() => location.reload(), 3000);
            } else {
                showToast('Failed to restart containers', 'error');
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

// Cleanup all
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
        showLoader('Cleaning up all containers... This may take a while.');
        showToast('Cleaning up all containers...', 'warning');

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000);

        try {
            const response = await fetch('/api/cleanup-all', { 
                method: 'POST',
                signal: controller.signal,
                keepalive: false
            });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (response.ok) {
                showToast(`Successfully cleaned up ${data.removed} containers`, 'success');
                hideLoader();
                setTimeout(() => location.reload(), 2000);
            } else {
                showToast('Cleanup failed', 'error');
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

// Load system info - CON DEBOUNCING
let loadSystemInfoDebounceTimer = null;
async function loadSystemInfo() {
    // Debounce
    if (loadSystemInfoDebounceTimer) {
        //console.log('loadSystemInfo: Debounced, skipping');
        return;
    }
    
    loadSystemInfoDebounceTimer = setTimeout(() => {
        loadSystemInfoDebounceTimer = null;
    }, 2000);
    
    //console.log('loadSystemInfo: Attempting refresh at', new Date().toISOString());
    
    if (operationInProgress) {
        //console.log('loadSystemInfo: Skipped - operation in progress');
        return;
    }
    
    //console.log('loadSystemInfo: Starting fetch to /api/system-info');
    
    try {
        const startTime = Date.now();
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch('/api/system-info', { signal: controller.signal });
        clearTimeout(timeoutId);
        
        const responseTime = (Date.now() - startTime) / 1000;
        //console.log('loadSystemInfo: Response received after', responseTime + 's');
        
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
        //console.log('loadSystemInfo: UI updated successfully');
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
        //console.log('initializeSystemInfo: Already initialized');
        return;
    }
    
    //console.log('initializeSystemInfo: First initialization');
    isInitialized = true;
    
    loadSystemInfo();
    
    if (systemInfoInterval) {
        clearInterval(systemInfoInterval);
    }
    
    //console.log('initializeSystemInfo: Starting interval every 30s');
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
    //console.log('beforeunload: Cleaning up');
    if (systemInfoInterval) {
        clearInterval(systemInfoInterval);
        systemInfoInterval = null;
    }
});