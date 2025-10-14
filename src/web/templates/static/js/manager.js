// Operation state management
const OperationState = {
    inProgress: false,
    systemInfoInterval: null,
    debounceTimer: null,
    isInitialized: false
};

// Operation configuration
const OperationConfig = {
    timeout: 120000, // 120 seconds
    pollInterval: 1000,
    maxPollAttempts: 180,
    systemInfoUpdateInterval: 30000
};

// Operation types configuration
const OPERATION_TYPES = {
    stop: {
        verb: 'Stopping',
        field: 'stopped',
        emoji: '⏹️',
        action: 'stopped'
    },
    restart: {
        verb: 'Restarting',
        field: 'restarted',
        emoji: '🔄',
        action: 'restarted'
    },
    cleanup: {
        verb: 'Cleaning up',
        field: 'removed',
        emoji: '🧹',
        action: 'cleaned up'
    }
};

// Toast configuration
const TOAST_CONFIG = {
    duration: 4000,
    animationDelay: 10,
    icons: {
        success: '✓',
        error: '✗',
        info: 'ℹ️',
        warning: '⚠️'
    }
};

// Modal Management
const ModalManager = {
    open(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('modal-open');
            document.body.style.overflow = 'hidden';
        }
    },

    close(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('modal-open');
            document.body.style.overflow = '';
        }
    }
};

// Toast System
class ToastManager {
    static show(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = this.createToast(message, type);
        container.appendChild(toast);

        this.animateToast(toast);
    }

    static createToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${TOAST_CONFIG.icons[type] || 'ℹ️'}</span>
            <span class="toast-message">${message}</span>
        `;
        return toast;
    }

    static animateToast(toast) {
        setTimeout(() => toast.classList.add('toast-show'), TOAST_CONFIG.animationDelay);

        setTimeout(() => {
            toast.classList.remove('toast-show');
            setTimeout(() => toast.remove(), 300);
        }, TOAST_CONFIG.duration);
    }
}

// API Service
class ApiService {
    static async fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), options.timeout || OperationConfig.timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    static async fetchJson(url, options = {}) {
        const response = await this.fetchWithTimeout(url, options);
        return response.json();
    }

    static async fetchText(url, options = {}) {
        const response = await this.fetchWithTimeout(url, options);
        return response.text();
    }
}

// Operation Poller
class OperationPoller {
    static async poll(operationId, operationType, groupName = null) {
        const config = OPERATION_TYPES[operationType];
        if (!config) {
            throw new Error(`Unknown operation type: ${operationType}`);
        }

        let attempts = 0;
        let totalContainers = '?';

        const poll = async () => {
            try {
                const statusData = await ApiService.fetchJson(`/api/operation-status/${operationId}`);

                // Update total when available
                if (statusData.total !== undefined) {
                    totalContainers = statusData.total;
                }

                this.updateProgress(statusData, config, totalContainers, groupName);

                if (statusData.status === 'completed') {
                    this.handleCompletion(statusData, config, operationType, groupName);
                    return;
                }

                if (statusData.status === 'error') {
                    this.handleError(statusData, config);
                    return;
                }

                attempts++;
                if (attempts >= OperationConfig.maxPollAttempts) {
                    this.handleTimeout();
                    return;
                }

                setTimeout(poll, OperationConfig.pollInterval);
            } catch (error) {
                this.handlePollingError(error, attempts, poll);
            }
        };

        this.showInitialLoader(config, groupName);
        poll();
    }

    static updateProgress(statusData, config, totalContainers, groupName) {
        const completed = statusData[config.field] || 0;
        const remaining = totalContainers !== '?' ? totalContainers - completed : '?';
        const prefix = groupName ? `${config.verb} '${groupName}':` : `${config.verb} containers:`;

        showLoader(`${prefix} ${completed} of ${totalContainers} completed (${remaining} remaining)`);
    }

    static handleCompletion(statusData, config, operationType, groupName) {
        const completed = statusData[config.field] || 0;
        const action = config.action || operationType;
        const message = groupName
            ? `${config.emoji} Successfully ${action} stack '${groupName}'! Reloading page...`
            : `${config.emoji} Successfully ${action} ${completed} containers! Reloading page...`;

        ToastManager.show(message, 'success');
        hideLoader();

        setTimeout(() => location.reload(), 2500);
    }

    static handleError(statusData, config) {
        ToastManager.show(`❌ ${config.verb} operation failed: ${statusData.error}`, 'error');
        hideLoader();
        resumeSystemInfoUpdates();
    }

    static handleTimeout() {
        ToastManager.show(`⏰ Operation timed out after ${OperationConfig.maxPollAttempts} seconds. Please check the page or refresh manually.`, 'warning');
        hideLoader();
        resumeSystemInfoUpdates();
    }

    static handlePollingError(error, attempts, retryCallback) {
        console.error('Polling error:', error);

        if (attempts < OperationConfig.maxPollAttempts) {
            setTimeout(retryCallback, OperationConfig.pollInterval);
        } else {
            ToastManager.show('❌ Polling failed after maximum attempts', 'error');
            hideLoader();
            resumeSystemInfoUpdates();
        }
    }

    static showInitialLoader(config, groupName) {
        const message = groupName
            ? `${config.verb} '${groupName}': 0 of ? completed...`
            : `${config.verb} containers: 0 of ? completed...`;

        showLoader(message);
    }
}

// System Info Manager
class SystemInfoManager {
    static async load() {
        // Debounce
        if (OperationState.debounceTimer || OperationState.inProgress) {
            return;
        }

        OperationState.debounceTimer = setTimeout(() => {
            OperationState.debounceTimer = null;
        }, 2000);

        try {
            const data = await ApiService.fetchJson('/api/system-info', { timeout: 5000 });
            this.updateUI(data);
        } catch (error) {
            this.handleError(error);
        }
    }

    static updateUI(data) {
        // Update statistics
        this.updateElementText('stat-total', data.counts.total);
        this.updateElementText('stat-running', data.counts.running);
        this.updateElementText('stat-stopped', data.counts.stopped);

        // Update system information
        this.updateElementText('docker-info',
            `Version: ${data.docker.version}\nContainers: ${data.docker.containers}\nImages: ${data.docker.images}`);

        this.updateElementText('network-info',
            `Name: ${data.network.name}\nDriver: ${data.network.driver}\nSubnet: ${data.network.subnet || 'N/A'}`);

        this.updateElementText('volume-info',
            `Path: ${data.volume.path}\nSize: ${data.volume.size || 'N/A'}`);

        // Update active containers list
        this.updateActiveContainers(data.active_containers);
    }

    static updateElementText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        }
    }

    static updateActiveContainers(containers) {
        const activeList = document.getElementById('active-list');
        if (!activeList) return;

        if (!containers || containers.length === 0) {
            activeList.innerHTML = '<p style="color: #64748b;">No active containers</p>';
        } else {
            activeList.innerHTML = containers.map(container =>
                `<div class="active-container-item">
                    <span>🐳 ${container.name}</span>
                    <span class="container-status">${container.status}</span>
                </div>`
            ).join('');
        }
    }

    static handleError(error) {
        if (error.name === 'AbortError') {
            console.error('SystemInfoManager: Timeout after 5s');
        } else {
            console.error('SystemInfoManager: Failed to load system info:', error);
        }
    }

    static initialize() {
        if (OperationState.isInitialized) return;

        OperationState.isInitialized = true;
        this.load();

        // Clear existing interval
        if (OperationState.systemInfoInterval) {
            clearInterval(OperationState.systemInfoInterval);
        }

        // Set up periodic updates
        OperationState.systemInfoInterval = setInterval(
            () => this.load(),
            OperationConfig.systemInfoUpdateInterval
        );
    }

    static cleanup() {
        if (OperationState.systemInfoInterval) {
            clearInterval(OperationState.systemInfoInterval);
            OperationState.systemInfoInterval = null;
        }
    }
}

// Operation Handlers
class OperationHandlers {
    static async performBulkOperation(apiEndpoint, operationType, confirmTitle, confirmMessage, confirmType = 'warning') {
        try {
            const confirmed = await showConfirmModal(confirmTitle, confirmMessage, confirmType);
            if (!confirmed) return;

            pauseSystemInfoUpdates();
            ToastManager.show(`Initiating ${operationType} operation...`, 'info');

            const data = await ApiService.fetchJson(apiEndpoint, {
                method: 'POST'
            });

            if (data.operation_id) {
                OperationPoller.poll(data.operation_id, operationType);
            } else {
                throw new Error('No operation ID received');
            }
        } catch (error) {
            this.handleOperationError(error, operationType);
        }
    }

    static async stopAll() {
        await this.performBulkOperation(
            '/api/stop-all',
            'stop',
            'Stop All Containers',
            'Are you sure you want to stop ALL running containers? This will gracefully stop all running playground containers.',
            'danger'
        );
    }

    static async restartAll() {
        await this.performBulkOperation(
            '/api/restart-all',
            'restart',
            'Restart All Containers',
            'Are you sure you want to restart ALL running containers? This will restart all containers one by one.',
            'warning'
        );
    }

    static async cleanupAll() {
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
            ToastManager.show('Initiating cleanup all operation...', 'warning');

            const data = await ApiService.fetchJson('/api/cleanup-all', {
                method: 'POST'
            });

            if (data.operation_id) {
                OperationPoller.poll(data.operation_id, 'cleanup');
            } else {
                throw new Error('No operation ID received');
            }
        } catch (error) {
            this.handleOperationError(error, 'cleanup');
        }
    }

    static handleOperationError(error, operationType) {
        if (error.name === 'AbortError') {
            ToastManager.show('⏰ Operation request timed out - please check server status', 'warning');
        } else {
            ToastManager.show(`❌ ${operationType} operation failed: ${error.message}`, 'error');
        }
        hideLoader();
        resumeSystemInfoUpdates();
    }
}

// Group Operations
class GroupOperations {
    static async startGroup(groupName, fromManagePage = false) {
        try {
            const confirmed = await showConfirmModal(
                'Start Application Stack',
                `Start all containers in <strong>${groupName}</strong>?`,
                'success'
            );
            if (!confirmed) return;

            pauseSystemInfoUpdates();
            showLoader(`Initiating start for '${groupName}'...`);
            ToastManager.show(`Starting ${groupName}...`, 'info');

            const data = await ApiService.fetchJson(`/api/start-group/${encodeURIComponent(groupName)}`, {
                method: 'POST'
            });

            if (fromManagePage) {
                this.pollStartGroupStatusManager(data.operation_id, groupName);
            } else {
                OperationPoller.poll(data.operation_id, 'start', groupName);
            }
        } catch (error) {
            this.handleGroupOperationError(error, 'start');
        }
    }

    static async stopGroup(groupName, fromManagePage = false) {
        try {
            const confirmed = await showConfirmModal(
                'Stop Application Stack',
                `Stop all containers in <strong>${groupName}</strong>?`,
                'warning'
            );
            if (!confirmed) return;

            pauseSystemInfoUpdates();
            showLoader(`Initiating stop for '${groupName}'...`);

            const data = await ApiService.fetchJson(`/api/stop-group/${encodeURIComponent(groupName)}`, {
                method: 'POST'
            });

            if (fromManagePage) {
                this.pollStopGroupStatusManager(data.operation_id, groupName);
            } else {
                OperationPoller.poll(data.operation_id, 'stop', groupName);
            }
        } catch (error) {
            this.handleGroupOperationError(error, 'stop');
        }
    }

    static async pollStartGroupStatusManager(operationId, groupName) {
        // Implementation for manage page specific polling
        let attempts = 0;

        const poll = async () => {
            try {
                const statusData = await ApiService.fetchJson(`/api/operation-status/${operationId}`);
                this.updateGroupProgress(statusData, groupName, 'start');

                if (statusData.status === 'completed') {
                    this.handleGroupCompletion(statusData, groupName, 'start');
                    return;
                }

                if (statusData.status === 'error') {
                    this.handleGroupError(statusData, 'start');
                    return;
                }

                attempts++;
                if (attempts < OperationConfig.maxPollAttempts) {
                    setTimeout(poll, OperationConfig.pollInterval);
                } else {
                    this.handleGroupTimeout();
                }
            } catch (error) {
                this.handleGroupPollingError(error, attempts, poll);
            }
        };

        poll();
    }

    static async pollStopGroupStatusManager(operationId, groupName) {
        let attempts = 0;

        const poll = async () => {
            try {
                const statusData = await ApiService.fetchJson(`/api/operation-status/${operationId}`);
                this.updateStopGroupProgress(statusData, groupName);

                if (statusData.status === 'completed') {
                    this.handleStopGroupCompletion(statusData, groupName);
                    return;
                }

                if (statusData.status === 'error') {
                    this.handleStopGroupError(statusData);
                    return;
                }

                attempts++;
                if (attempts < OperationConfig.maxPollAttempts) {
                    setTimeout(poll, OperationConfig.pollInterval);
                } else {
                    this.handleStopGroupTimeout();
                }
            } catch (error) {
                this.handleStopGroupPollingError(error, attempts, poll);
            }
        };

        poll();
    }

    static updateStopGroupProgress(statusData, groupName) {
        const total = statusData.total || '?';
        const stopped = statusData.stopped || 0;
        const notRunning = statusData.not_running || 0;
        const failed = statusData.failed || 0;
        const completed = stopped + notRunning + failed;

        showLoader(
            `Stopping '${groupName}': ${completed}/${total} | ` +
            `⏹️ ${stopped}, ⏸️ ${notRunning}, ✗ ${failed}`
        );
    }

    static handleStopGroupCompletion(statusData, groupName) {
        const stopped = statusData.stopped || 0;
        const notRunning = statusData.not_running || 0;
        const failed = statusData.failed || 0;

        let message = `Stack '${groupName}': `;
        const details = [];
        if (stopped > 0) details.push(`${stopped} stopped`);
        if (notRunning > 0) details.push(`${notRunning} not running`);
        if (failed > 0) details.push(`${failed} failed`);

        if (details.length > 0) {
            message += details.join(', ');
        } else {
            message += 'No containers were running';
        }

        // Show detailed errors if present
        if (statusData.errors && statusData.errors.length > 0) {
            this.showErrorsAsToasts(statusData.errors, message, failed > 0 ? 'warning' : 'success');
        } else {
            ToastManager.show(message, failed > 0 ? 'warning' : 'success');
        }

        hideLoader();
        resumeSystemInfoUpdates();

        // Reload page after a short delay to reflect changes
        setTimeout(() => location.reload(), 2000);
    }

    static handleStopGroupError(statusData) {
        const errorMessage = statusData.error || 'Unknown error occurred during stop operation';
        ToastManager.show(`Stop failed: ${errorMessage}`, 'error');
        hideLoader();
        resumeSystemInfoUpdates();
    }

    static handleStopGroupTimeout() {
        ToastManager.show(`⏰ Stop operation timed out after ${OperationConfig.maxPollAttempts} seconds. Please check status manually.`, 'warning');
        hideLoader();
        resumeSystemInfoUpdates();
    }

    static handleStopGroupPollingError(error, attempts, retryCallback) {
        console.error('Stop group polling error:', error);

        if (attempts < OperationConfig.maxPollAttempts) {
            ToastManager.show('Connection issue, retrying...', 'warning');
            setTimeout(retryCallback, OperationConfig.pollInterval);
        } else {
            ToastManager.show('❌ Stop operation polling failed after maximum attempts', 'error');
            hideLoader();
            resumeSystemInfoUpdates();
        }
    }

    static updateGroupProgress(statusData, groupName, operation) {
        const total = statusData.total || '?';
        const started = statusData.started || 0;
        const alreadyRunning = statusData.already_running || 0;
        const failed = statusData.failed || 0;
        const completed = started + alreadyRunning + failed;

        showLoader(
            `${operation === 'start' ? 'Starting' : 'Stopping'} '${groupName}': ${completed}/${total} | ` +
            `✓ ${started}, ⚡ ${alreadyRunning}, ✗ ${failed}`
        );
    }

    static handleGroupCompletion(statusData, groupName, operation) {
        const started = statusData.started || 0;
        const alreadyRunning = statusData.already_running || 0;
        const failed = statusData.failed || 0;

        let message = `Stack '${groupName}': `;
        const details = [];
        if (started > 0) details.push(`${started} started`);
        if (alreadyRunning > 0) details.push(`${alreadyRunning} running`);
        if (failed > 0) details.push(`${failed} failed`);

        message += details.join(', ');

        if (statusData.errors && statusData.errors.length > 0) {
            this.showErrorsAsToasts(statusData.errors, message, failed > 0 ? 'warning' : 'success');
        } else {
            ToastManager.show(message, failed > 0 ? 'warning' : 'success');
        }

        hideLoader();
        resumeSystemInfoUpdates();
    }

    static handleGroupOperationError(error, operation) {
        if (error.name === 'AbortError') {
            ToastManager.show('Request timed out', 'warning');
        } else {
            ToastManager.show(`${operation} operation failed: ${error.message}`, 'error');
        }
        hideLoader();
        resumeSystemInfoUpdates();
    }

    static showErrorsAsToasts(errors, baseMessage, baseType = 'warning') {
        if (!errors || errors.length === 0) return;

        ToastManager.show(baseMessage, baseType);

        errors.forEach((error, index) => {
            setTimeout(() => {
                ToastManager.show(`Error: ${error}`, 'error');
            }, (index + 1) * 800);
        });
    }
}

// Utility Functions
function pauseSystemInfoUpdates() {
    OperationState.inProgress = true;
    if (OperationState.systemInfoInterval) {
        clearInterval(OperationState.systemInfoInterval);
        OperationState.systemInfoInterval = null;
    }
}

function resumeSystemInfoUpdates() {
    OperationState.inProgress = false;
    if (!OperationState.systemInfoInterval) {
        OperationState.systemInfoInterval = setInterval(
            () => SystemInfoManager.load(),
            OperationConfig.systemInfoUpdateInterval
        );
    }
    SystemInfoManager.load();
}

// Category // Category Operations
class CategoryOperations {
    static async startCategory(category) {
        try {
            const confirmed = await showConfirmModal(
                'Start Category',
                `Are you sure you want to start all containers in category: ${category}?`,
                'success'
            );
            if (!confirmed) return;

            await this.performCategoryOperation(category, 'start');
        } catch (error) {
            this.handleCategoryError(error, 'start');
        }
    }

    static async startByCategory() {
        try {
            const category = await showInputModal(
                'Start Category',
                'Enter the category name to start all its containers:',
                'e.g., linux, database, programming...'
            );
            if (!category) return;

            await this.performCategoryOperation(category, 'start');
        } catch (error) {
            this.handleCategoryError(error, 'start');
        }
    }

    static async performCategoryOperation(category, operation) {
        pauseSystemInfoUpdates();
        showLoader(`${operation === 'start' ? 'Starting' : 'Stopping'} containers in category ${category}...`);
        ToastManager.show(`${operation === 'start' ? 'Starting' : 'Stopping'} ${category} containers...`, 'info');

        const data = await ApiService.fetchJson(`/api/${operation}-category/${category}`, {
            method: 'POST'
        });

        if (data.started > 0) {
            ToastManager.show(`Successfully ${operation === 'start' ? 'started' : 'stopped'} ${data.started} containers`, 'success');
        } else {
            ToastManager.show(`No containers ${operation === 'start' ? 'started' : 'stopped'} in category: ${category}`, 'warning');
        }
        
        hideLoader();
        setTimeout(() => location.reload(), 2000);
    }

    static handleCategoryError(error, operation) {
        if (error.name === 'AbortError') {
            ToastManager.show('Operation timeout - please wait and refresh manually', 'warning');
            hideLoader();
            setTimeout(() => location.reload(), 5000);
        } else {
            ToastManager.show(`${operation} operation failed: ${error.message}`, 'error');
            hideLoader();
            resumeSystemInfoUpdates();
        }
    }
}

async function startCategory(category) {
    try {
        const confirmed = await showConfirmModal(
            'Start Category',
            `Are you sure you want to start all containers in category: ${category}?`,
            'success'
        );
        if (!confirmed) return;

        await performCategoryOperation(category, 'start');
    } catch (error) {
        handleCategoryError(error, 'start');
    }
}

async function startByCategory() {
    try {
        const category = await showInputModal(
            'Start Category',
            'Enter the category name to start all its containers:',
            'e.g., linux, database, programming...'
        );
        if (!category) return;

        await performCategoryOperation(category, 'start');
    } catch (error) {
        handleCategoryError(error, 'start');
    }
}

async function performCategoryOperation(category, operation) {
    pauseSystemInfoUpdates();
    showLoader(`${operation === 'start' ? 'Starting' : 'Stopping'} containers in category ${category}...`);
    ToastManager.show(`${operation === 'start' ? 'Starting' : 'Stopping'} ${category} containers...`, 'info');

    const data = await ApiService.fetchJson(`/api/${operation}-category/${category}`, {
        method: 'POST'
    });

    if (data.started > 0) {
        ToastManager.show(`Successfully ${operation === 'start' ? 'started' : 'stopped'} ${data.started} containers`, 'success');
    } else {
        ToastManager.show(`No containers ${operation === 'start' ? 'started' : 'stopped'} in category: ${category}`, 'warning');
    }

    hideLoader();
    setTimeout(() => location.reload(), 2000);
}

function handleCategoryError(error, operation) {
    if (error.name === 'AbortError') {
        ToastManager.show('Operation timeout - please wait and refresh manually', 'warning');
        hideLoader();
        setTimeout(() => location.reload(), 5000);
    } else {
        ToastManager.show(`${operation} operation failed: ${error.message}`, 'error');
        hideLoader();
        resumeSystemInfoUpdates();
    }
}

// View functions
function viewCategory(category) {
    window.location.href = `/?category=${category}`;
}

function viewGroup(groupName) {
    window.location.href = `/?group=${encodeURIComponent(groupName)}`;
}

// Backup functions
async function showBackups() {
    try {
        showLoader('Loading backups...');
        const data = await ApiService.fetchJson('/api/backups');
        this.renderBackupsList(data.backups);
        ModalManager.open('backupsModal');
    } catch (error) {
        ToastManager.show(`Error loading backups: ${error.message}`, 'error');
    } finally {
        hideLoader();
    }
}

function renderBackupsList(backups) {
    const list = document.getElementById('backupsList');
    if (!list) return;

    if (!backups || backups.length === 0) {
        list.innerHTML = '<p style="color: #64748b;">No backups found</p>';
    } else {
        list.innerHTML = this.createBackupsTable(backups);
    }
}

function createBackupsTable(backups) {
    const rows = backups.map(backup => `
        <tr>
            <td>${backup.category}</td>
            <td>${backup.file}</td>
            <td>${this.formatFileSize(backup.size)}</td>
            <td>${new Date(backup.modified * 1000).toLocaleString()}</td>
            <td><button class="btn btn-primary btn-sm" onclick="downloadBackup('${backup.category}', '${backup.file}')">Download</button></td>
        </tr>
    `).join('');

    return `
        <table class="backups-table">
            <thead>
                <tr>
                    <th>Category</th>
                    <th>File</th>
                    <th>Size</th>
                    <th>Modified</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

function formatFileSize(bytes) {
    if (bytes >= 1024 * 1024) {
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    } else if (bytes >= 1024) {
        return (bytes / 1024).toFixed(2) + ' KB';
    } else {
        return bytes + ' bytes';
    }
}

function downloadBackup(category, filename) {
    const url = `/api/download-backup/${encodeURIComponent(category)}/${encodeURIComponent(filename)}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    ToastManager.show(`Downloading ${filename}...`, 'info');
}

// Export configuration
async function exportConfig() {
    try {
        ToastManager.show('Exporting configuration...', 'info');

        const response = await ApiService.fetchWithTimeout('/api/export-config');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `playground-config-${new Date().toISOString().split('T')[0]}.yml`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        ToastManager.show('Configuration exported', 'success');
    } catch (error) {
        ToastManager.show(`Export failed: ${error.message}`, 'error');
    }
}

// Server Logs
async function showServerLogs() {
    try {
        showLoader('Loading server logs...');
        const logs = await ApiService.fetchText('/api/logs');
        document.getElementById('logContent').textContent = logs || 'No logs available';
        ModalManager.open('logModal');
    } catch (error) {
        ToastManager.show(`Error loading logs: ${error.message}`, 'error');
    } finally {
        hideLoader();
    }
}

// View functions
function viewCategory(category) {
    window.location.href = `/?category=${category}`;
}

function viewGroup(groupName) {
    window.location.href = `/?group=${encodeURIComponent(groupName)}`;
}

// Utility Functions
function pauseSystemInfoUpdates() {
    OperationState.inProgress = true;
    if (OperationState.systemInfoInterval) {
        clearInterval(OperationState.systemInfoInterval);
        OperationState.systemInfoInterval = null;
    }
}

function resumeSystemInfoUpdates() {
    OperationState.inProgress = false;
    if (!OperationState.systemInfoInterval) {
        OperationState.systemInfoInterval = setInterval(
            () => SystemInfoManager.load(), 
            OperationConfig.systemInfoUpdateInterval
        );
    }
    SystemInfoManager.load();
}

// Initialize application
function initializeApp() {
    if (OperationState.isInitialized) return;
    
    SystemInfoManager.initialize();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', SystemInfoManager.cleanup);
}

// Global exports for HTML onclick handlers
window.OperationHandlers = OperationHandlers;
window.GroupOperations = GroupOperations;
window.CategoryOperations = CategoryOperations;
window.ModalManager = ModalManager;
window.showBackups = showBackups;
window.downloadBackup = downloadBackup;
window.exportConfig = exportConfig;
window.showServerLogs = showServerLogs;
window.viewCategory = viewCategory;
window.viewGroup = viewGroup;

// Load on page ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}