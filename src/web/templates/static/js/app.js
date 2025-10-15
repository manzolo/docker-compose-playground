// =========================================================
// Global State Management
// =========================================================
const AppState = {
    ws: null,
    term: null,
    fitAddon: null,
    webglAddon: null,
    activeStatusFilter: 'all'
};

// =========================================================
// DOM Elements Cache
// =========================================================
const DOM = {
    get filterInput() { return document.getElementById('filter'); },
    get searchCount() { return document.getElementById('search-count'); },
    get categoryFilter() { return document.getElementById('category-filter'); },
    get imageCards() { return document.querySelectorAll('.image-card'); },
    get filterButtons() { return document.querySelectorAll('.filter-btn'); },
    get toastContainer() { return document.getElementById('toast-container'); }
};

// =========================================================
// Constants
// =========================================================
const Constants = {
    POLLING: {
        MAX_ATTEMPTS: 180,
        INTERVAL: 1000,
        TIMEOUT: {
            START: 180000,
            STOP: 180000,
            GROUP: 10000
        }
    },
    TOAST: {
        DISPLAY_TIME: 4000,
        DELAY_BEFORE_RELOAD: 2500
    },
    ICONS: {
        success: '✓',
        error: '✗',
        info: 'ℹ',
        warning: '⚠'
    }
};

// =========================================================
// Utility Functions
// =========================================================
const Utils = {
    /**
     * Creates an abort controller with timeout
     */
    createAbortController(timeoutMs) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        return { controller, timeoutId };
    },

    /**
     * Clears abort controller timeout
     */
    clearAbortTimeout(timeoutId) {
        if (timeoutId) clearTimeout(timeoutId);
    },

    /**
     * Parses HTML response to DOM
     */
    parseHTMLResponse(text) {
        const parser = new DOMParser();
        return parser.parseFromString(text, 'text/html');
    },

    /**
     * Updates button state during async operations
     */
    updateButtonState(button, options = {}) {
        const {
            disabled = false,
            text = '',
            showSpinner = false,
            originalHTML = null
        } = options;

        if (disabled !== undefined) button.disabled = disabled;

        if (text) {
            button.innerHTML = showSpinner
                ? `<span class="spinner"></span> ${text}`
                : text;
        } else if (originalHTML) {
            button.innerHTML = originalHTML;
        }
    },

    /**
   * Generic polling function for operation status
   * @param {string} operationId - ID of the operation to poll
   * @param {function} messageFormatter - Function to format loader message
   * @param {Object} options - Polling options
   * @returns {Promise<Object>} Final status data
   */
    async pollOperationStatus(operationId, messageFormatter, options = {}) {
        const { maxAttempts = Constants.POLLING.MAX_ATTEMPTS, interval = Constants.POLLING.INTERVAL } = options;
        let attempts = 0;

        const poll = async () => {
            try {
                const response = await fetch(`/api/operation-status/${operationId}`);
                const statusData = await response.json();

                // Mostra il messaggio di progresso
                if (messageFormatter) {
                    showLoader(messageFormatter(statusData));
                }

                // Gestisci stato completato o errore
                if (statusData.status === 'completed' || statusData.status === 'error') {
                    hideLoader();
                    return statusData;
                }

                attempts++;
                if (attempts < maxAttempts) {
                    return new Promise(resolve => setTimeout(() => resolve(poll()), interval));
                } else {
                    throw new Error(`Operation timed out after ${maxAttempts} attempts`);
                }
            } catch (error) {
                console.error('Polling error:', error);
                attempts++;
                if (attempts < maxAttempts) {
                    return new Promise(resolve => setTimeout(() => resolve(poll()), interval));
                } else {
                    throw error;
                }
            }
        };

        return poll();
    }
};

// =========================================================
// Toast Notification System
// =========================================================
const ToastManager = {
    show(message, type = 'info') {
        const container = DOM.toastContainer;
        if (!container) {
            console.warn('Toast container is missing. Message:', message);
            return;
        }

        const toast = this.createToast(message, type);
        container.appendChild(toast);

        this.animateToast(toast);
    },

    createToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${Constants.ICONS[type]}</span>
            <span class="toast-message">${message}</span>
        `;
        return toast;
    },

    animateToast(toast) {
        setTimeout(() => toast.classList.add('toast-show'), 10);

        setTimeout(() => {
            toast.classList.remove('toast-show');
            setTimeout(() => toast.remove(), 300);
        }, Constants.TOAST.DISPLAY_TIME);
    },

    showErrorsSequentially(errors, baseMessage = 'Errors:') {
        if (!errors || errors.length === 0) return;

        this.show(baseMessage, 'warning');

        errors.forEach((error, index) => {
            setTimeout(() => {
                this.show(`Error: ${error}`, 'error');
            }, (index + 1) * 800);
        });
    }
};

// =========================================================
// Filter Management
// =========================================================
const FilterManager = {
    init() {
        if (DOM.filterInput) {
            DOM.filterInput.addEventListener('input', () => this.applyFilters());
        }
        if (DOM.categoryFilter) {
            DOM.categoryFilter.addEventListener('change', () => this.applyFilters());
        }

        this.applyFilters();
    },

    applyFilters() {
        const searchTerm = DOM.filterInput?.value.toLowerCase() || '';
        const selectedCategory = DOM.categoryFilter?.value.toLowerCase() || '';

        DOM.imageCards.forEach(card => {
            const matches = this.cardMatchesFilters(card, searchTerm, selectedCategory);
            card.style.display = matches ? '' : 'none';
        });

        this.updateCounts();
    },

    cardMatchesFilters(card, searchTerm, selectedCategory) {
        const name = card.getAttribute('data-name').toLowerCase();
        const category = card.getAttribute('data-category').toLowerCase();
        const status = card.querySelector('.status-text').textContent.toLowerCase();

        const matchesSearch = searchTerm ?
            (name.includes(searchTerm) || category.includes(searchTerm)) : true;
        const matchesCategory = selectedCategory ?
            category === selectedCategory : true;
        const matchesStatus = AppState.activeStatusFilter === 'all' ?
            true : status === AppState.activeStatusFilter;

        return matchesSearch && matchesCategory && matchesStatus;
    },

    updateCounts() {
        let allCount = 0;
        let runningCount = 0;
        let stoppedCount = 0;

        DOM.imageCards.forEach(card => {
            const status = card.querySelector('.status-text').textContent.toLowerCase();
            if (status === 'running') runningCount++;
            else stoppedCount++;

            if (card.style.display !== 'none') allCount++;
        });

        this.updateCountElements(allCount, runningCount, stoppedCount);
    },

    updateCountElements(allCount, runningCount, stoppedCount) {
        const allElement = document.getElementById('count-all');
        const runningElement = document.getElementById('count-running');
        const stoppedElement = document.getElementById('count-stopped');

        if (allElement) allElement.textContent = allCount;
        if (runningElement) runningElement.textContent = runningCount;
        if (stoppedElement) stoppedElement.textContent = stoppedCount;
        if (DOM.searchCount) {
            DOM.searchCount.textContent = `${allCount} of ${DOM.imageCards.length} containers`;
        }
    },

    filterByStatus(status) {
        AppState.activeStatusFilter = status;

        DOM.filterButtons.forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-filter') === status);
        });

        this.applyFilters();
    },

    clearSearch() {
        if (DOM.filterInput) {
            DOM.filterInput.value = '';
            DOM.filterInput.focus();
            this.applyFilters();
            ToastManager.show('🔄 Search cleared', 'info');
        }
    },

    quickSearchContainer(containerName) {
        if (DOM.filterInput) {
            DOM.filterInput.value = containerName;
            DOM.filterInput.focus();
            this.applyFilters();
            this.highlightMatchingCard(containerName);
            ToastManager.show(`🔍 Filtered to: ${containerName}`, 'info');
        }
    },

    highlightMatchingCard(containerName) {
        const imageGrid = document.querySelector('.image-grid');
        if (imageGrid) {
            imageGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

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
    }
};

// =========================================================
// Container Management - FIXED VERSION
// =========================================================
const ContainerManager = {
    async startContainer(image) {
        const card = document.querySelector(`[data-name="${image}"]`);
        const btn = card?.querySelector('.btn-success');
        if (!btn) return;

        const originalHTML = btn.innerHTML;
        Utils.updateButtonState(btn, {
            disabled: true,
            text: 'Starting...',
            showSpinner: true
        });

        try {
            showLoader(`Initiating start for container ${image}...`);
            const { controller, timeoutId } = Utils.createAbortController(Constants.POLLING.TIMEOUT.START);

            const response = await fetch(`/api/start/${encodeURIComponent(image)}`, {
                method: 'POST',
                signal: controller.signal
            });

            Utils.clearAbortTimeout(timeoutId);
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to start container');
            }

            const data = await response.json();
            
            // ✅ FIXED: Ora aspettiamo sempre un operation_id
            if (data.operation_id) {
                ToastManager.show(`Starting container ${image}...`, 'info');
                await this.pollContainerStatus(data.operation_id, image, btn, originalHTML);
            } else {
                // Fallback nel caso improbabile che non ci sia operation_id
                throw new Error('No operation_id received from server');
            }

        } catch (error) {
            this.handleStartError(error, image, btn, originalHTML);
        }
    },

    async pollContainerStatus(operationId, image, btn, originalHTML) {
        try {
            const statusData = await Utils.pollOperationStatus(
                operationId,
                (data) => this.formatContainerStatusMessage(data, image),
                { 
                    maxAttempts: Constants.POLLING.MAX_ATTEMPTS, 
                    interval: Constants.POLLING.INTERVAL 
                }
            );

            if (statusData.status === 'completed') {
                const started = statusData.started || 0;
                const alreadyRunning = statusData.already_running || 0;
                
                if (started > 0) {
                    ToastManager.show(`✅ Container ${image} started successfully!`, 'success');
                } else if (alreadyRunning > 0) {
                    ToastManager.show(`ℹ️ Container ${image} was already running`, 'info');
                }
                
                // Aggiorna UI
                this.updateCardUI(image, true, statusData.container || `playground-${image}`);
                
                // Ricarica pagina dopo un breve delay
                setTimeout(() => location.reload(), Constants.TOAST.DELAY_BEFORE_RELOAD);
                
            } else if (statusData.status === 'error') {
                const errorMsg = statusData.error || 'Unknown error';
                ToastManager.show(`❌ Failed to start ${image}: ${errorMsg}`, 'error');
                
                if (statusData.errors && statusData.errors.length > 0) {
                    ToastManager.showErrorsSequentially(statusData.errors, `Errors starting ${image}:`);
                }
                
                Utils.updateButtonState(btn, {
                    disabled: false,
                    originalHTML
                });
            }
        } catch (error) {
            ToastManager.show(`❌ Error polling container status: ${error.message}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML
            });
        }
    },

    formatContainerStatusMessage(statusData, image) {
        const total = statusData.total || 1;
        const started = statusData.started || 0;
        const alreadyRunning = statusData.already_running || 0;
        const failed = statusData.failed || 0;
        const completed = started + alreadyRunning + failed;
        const remaining = total - completed;

        if (statusData.status === 'running') {
            return `Starting '${image}': ${completed}/${total} | ` +
                `✓ ${started} started, ` +
                `⚡ ${alreadyRunning} already running, ` +
                `✗ ${failed} failed, ` +
                `⏳ ${remaining} remaining`;
        } else if (statusData.status === 'completed') {
            return `Container '${image}' started successfully! ✅`;
        } else {
            return `Starting container '${image}'...`;
        }
    },

    handleStartError(error, image, btn, originalHTML) {
        hideLoader();
        if (error.name === 'AbortError') {
            ToastManager.show(`⏰ Timeout starting ${image} - check container logs`, 'warning');
            setTimeout(() => location.reload(), Constants.TOAST.DELAY_BEFORE_RELOAD);
        } else {
            ToastManager.show(`❌ Error: ${error.message}`, 'error');
        }
        Utils.updateButtonState(btn, {
            disabled: false,
            originalHTML
        });
    },

    async stopContainer(imageName, containerName) {
        try {
            const confirmed = await showConfirmModal(
                'Stop Container',
                `Are you sure you want to stop container <strong>${containerName}</strong>? Any unsaved data might be lost.`,
                'warning'
            );
            if (!confirmed) return;

            await this.performStopContainer(imageName, containerName);
        } catch (error) {
            ToastManager.show(`❌ Error: ${error.message}`, 'error');
            this.resetStopButton(imageName);
        }
    },

    async performStopContainer(imageName, containerName) {
        const card = document.querySelector(`[data-name="${imageName}"]`);
        const btn = card?.querySelector('.btn-danger');
        if (!btn) return;

        const originalHTML = btn.innerHTML;
        Utils.updateButtonState(btn, {
            disabled: true,
            text: 'Stopping...',
            showSpinner: true
        });

        showLoader(`Stopping container ${containerName}...`);

        try {
            const { controller, timeoutId } = Utils.createAbortController(Constants.POLLING.TIMEOUT.STOP);

            const response = await fetch(`/stop/${containerName}`, {
                method: 'POST',
                signal: controller.signal
            });

            Utils.clearAbortTimeout(timeoutId);
            await this.handleStopResponse(response, imageName, containerName, btn);

        } catch (error) {
            this.handleStopError(error, containerName, btn, originalHTML);
        } finally {
            hideLoader();
        }
    },

    async handleStopResponse(response, imageName, containerName, btn) {
        if (response.ok) {
            ToastManager.show(`✅ Container ${containerName} stopped`, 'success');
            this.updateCardUI(imageName, false, '');
        } else {
            const data = await response.json();
            const errorMsg = data.detail || 'Failed to stop container';
            ToastManager.show(`❌ Error: ${errorMsg}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML: btn.innerHTML
            });
        }
    },

    handleStopError(error, containerName, btn, originalHTML) {
        if (error.name === 'AbortError') {
            ToastManager.show(`⏰ Timeout stopping ${containerName} - container may still be stopping`, 'warning');
            Utils.updateButtonState(btn, {
                text: 'Stopping...',
                showSpinner: true
            });

            setTimeout(() => {
                ToastManager.show('🔄 Reloading to check status...', 'info');
                location.reload();
            }, 3000);
        } else {
            ToastManager.show(`❌ Error: ${error.message}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML
            });
        }
    },

    resetStopButton(imageName) {
        const card = document.querySelector(`[data-name="${imageName}"]`);
        const btn = card?.querySelector('.btn-danger');
        if (btn) {
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML: '<span class="btn-icon">⏹</span> Stop'
            });
        }
    },

    updateCardUI(imageName, isRunning, containerName) {
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
                <button class="btn btn-danger" onclick="ContainerManager.stopContainer('${imageName}', '${containerName}')">
                    <span class="btn-icon">⏹</span> Stop
                </button>
                <button class="btn btn-primary" onclick="showLogs('${containerName}')">
                    <span class="btn-icon">📋</span> Logs
                </button>
                <button class="btn btn-success" onclick="ConsoleManager.open('${containerName}', '${imageName}')">
                    <span class="btn-icon">💻</span> Console
                </button>
            `;
        } else {
            card.removeAttribute('data-container');
            statusIndicator.className = 'status-indicator status-stopped';
            statusText.textContent = 'Stopped';
            actions.innerHTML = `
                <button class="btn btn-success btn-block" onclick="ContainerManager.startContainer('${imageName}')">
                    <span class="btn-icon">▶</span> Start Container
                </button>
            `;
        }

        FilterManager.applyFilters();
    }
};

// =========================================================
// Console Management
// =========================================================
const ConsoleManager = {
    open(container, imageName) {
        this.updateConsoleUI(container, '● Connecting...', 'console-connecting');
        openModal('consoleModal');
        this.initializeTerminal();
        this.connectWebSocket(container);
    },

    updateConsoleUI(container, status, className) {
        document.getElementById('consoleContainerName').textContent = container;
        const statusElement = document.getElementById('consoleStatus');
        statusElement.textContent = status;
        statusElement.className = `console-status ${className}`;
    },

    initializeTerminal() {
        if (AppState.term) {
            AppState.term.dispose();
            AppState.term = null;
        }

        AppState.term = new Terminal({
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

        AppState.fitAddon = new FitAddon.FitAddon();
        AppState.term.loadAddon(AppState.fitAddon);

        try {
            AppState.webglAddon = new WebglAddon.WebglAddon();
            AppState.term.loadAddon(AppState.webglAddon);
        } catch (error) {
            console.warn('WebGL addon not available, using canvas renderer');
        }

        AppState.term.open(document.getElementById('terminal'));
        AppState.fitAddon.fit();
        AppState.term.focus();

        window.addEventListener('resize', () => {
            if (AppState.fitAddon) AppState.fitAddon.fit();
        });
    },

    connectWebSocket(container) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        AppState.ws = new WebSocket(`${protocol}//${window.location.host}/ws/console/${container}`);

        AppState.ws.onopen = () => {
            this.updateConsoleUI(container, '● Connected', 'console-connected');
            AppState.term.write('\r\n\x1b[32m✓ Connected to console\x1b[0m\r\n\r\n');
        };

        AppState.ws.onmessage = (event) => {
            AppState.term.write(event.data);
            AppState.term.scrollToBottom();
        };

        AppState.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConsoleUI(container, '● Error', 'console-error');
            AppState.term.write('\r\n\x1b[31m✗ Connection error\x1b[0m\r\n');
        };

        AppState.ws.onclose = () => {
            this.updateConsoleUI(container, '● Disconnected', 'console-disconnected');
            if (AppState.term) {
                AppState.term.write('\r\n\x1b[33m⚠ Console disconnected\x1b[0m\r\n');
            }
        };

        AppState.term.onData(data => {
            if (AppState.ws && AppState.ws.readyState === WebSocket.OPEN) {
                AppState.ws.send(data);
            }
        });
    },

    close() {
        if (AppState.ws) {
            AppState.ws.onclose = null;
            AppState.ws.close();
            AppState.ws = null;
        }

        if (AppState.term) {
            if (AppState.webglAddon) {
                try {
                    AppState.webglAddon.dispose();
                } catch (error) {
                    console.warn('Error disposing WebGL addon:', error);
                }
                AppState.webglAddon = null;
            }
            AppState.term.dispose();
            AppState.term = null;
        }

        AppState.fitAddon = null;
        closeModal('consoleModal');
    }
};

// =========================================================
// Group Operations
// =========================================================
const GroupManager = {
    async startGroup(groupName) {
        const button = event.target;
        const originalText = button.textContent;

        button.textContent = '🔄 Starting...';
        button.disabled = true;

        try {
            showLoader(`Initiating start for group '${groupName}'...`);

            const { controller, timeoutId } = Utils.createAbortController(Constants.POLLING.TIMEOUT.GROUP);

            const response = await fetch(`/api/start-group/${encodeURIComponent(groupName)}`, {
                method: 'POST',
                signal: controller.signal
            });

            Utils.clearAbortTimeout(timeoutId);
            await this.handleStartGroupResponse(response, groupName, button, originalText);

        } catch (error) {
            this.handleGroupError(error, button, originalText, 'starting');
        }
    },

    async handleStartGroupResponse(response, groupName, button, originalText) {
        const data = await response.json();

        if (response.ok) {
            ToastManager.show(`Starting group '${groupName}'...`, 'info');
            this.pollStartGroupStatus(data.operation_id, groupName);
        } else {
            ToastManager.show(`Error: ${data.detail || 'Failed to start group'}`, 'error');
            hideLoader();
            button.textContent = originalText;
            button.disabled = false;
        }
    },

    async stopGroup(groupName) {
        try {
            const confirmed = await showConfirmModal(
                'Stop Group',
                `Are you sure you want to stop all containers in group '<strong>${groupName}</strong>'?`,
                'warning'
            );

            if (!confirmed) return;

            showLoader(`Initiating stop for group '${groupName}'...`);

            const { controller, timeoutId } = Utils.createAbortController(Constants.POLLING.TIMEOUT.GROUP);

            const response = await fetch(`/api/stop-group/${encodeURIComponent(groupName)}`, {
                method: 'POST',
                signal: controller.signal
            });

            Utils.clearAbortTimeout(timeoutId);
            await this.handleStopGroupResponse(response, groupName);

        } catch (error) {
            this.handleGroupError(error, null, null, 'stopping');
        }
    },

    async handleStopGroupResponse(response, groupName) {
        const data = await response.json();

        if (response.ok) {
            ToastManager.show(`Stopping group '${groupName}'...`, 'info');
            this.pollStopGroupStatus(data.operation_id, groupName);
        } else {
            ToastManager.show(`Error: ${data.detail || 'Failed to stop group'}`, 'error');
            hideLoader();
        }
    },

    handleGroupError(error, button, originalText, operation) {
        if (error.name === 'AbortError') {
            ToastManager.show('Request timed out', 'warning');
        } else {
            ToastManager.show(`Error ${operation} group`, 'error');
            console.error(`Error ${operation} group:`, error);
        }

        hideLoader();

        if (button && originalText) {
            button.textContent = originalText;
            button.disabled = false;
        }
    },

    async pollStartGroupStatus(operationId, groupName) {
        await this.pollGroupStatus(
            operationId,
            groupName,
            'start',
            (statusData) => this.formatStartGroupMessage(statusData, groupName)
        );
    },

    async pollStopGroupStatus(operationId, groupName) {
        await this.pollGroupStatus(
            operationId,
            groupName,
            'stop',
            (statusData) => this.formatStopGroupMessage(statusData, groupName)
        );
    },

    async pollGroupStatus(operationId, groupName, operationType, messageFormatter) {
        let attempts = 0;

        const poll = async () => {
            try {
                const response = await fetch(`/api/operation-status/${operationId}`);
                const statusData = await response.json();

                showLoader(messageFormatter(statusData));

                if (statusData.status === 'completed') {
                    hideLoader();
                    this.handleGroupOperationComplete(statusData, groupName, operationType);
                    return;
                }

                if (statusData.status === 'error') {
                    ToastManager.show(`${operationType} group failed: ${statusData.error}`, 'error');
                    hideLoader();
                    return;
                }

                attempts++;
                if (attempts < Constants.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Constants.POLLING.INTERVAL);
                } else {
                    ToastManager.show(`Operation timed out after ${Constants.POLLING.MAX_ATTEMPTS} seconds. Check status manually.`, 'warning');
                    hideLoader();
                }

            } catch (error) {
                console.error('Polling error:', error);
                attempts++;
                if (attempts < Constants.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Constants.POLLING.INTERVAL);
                } else {
                    ToastManager.show('Polling failed. Please refresh the page.', 'error');
                    hideLoader();
                }
            }
        };

        poll();
    },

    formatStartGroupMessage(statusData, groupName) {
        const total = statusData.total || '?';
        const started = statusData.started || 0;
        const alreadyRunning = statusData.already_running || 0;
        const failed = statusData.failed || 0;
        const completed = started + alreadyRunning + failed;
        const remaining = total !== '?' ? total - completed : '?';

        return `Starting '${groupName}': ${completed}/${total} | ` +
            `✓ ${started} started, ` +
            `⚡ ${alreadyRunning} running, ` +
            `✗ ${failed} failed, ` +
            `⏳ ${remaining} remaining`;
    },

    formatStopGroupMessage(statusData, groupName) {
        const total = statusData.total || 0;
        const stopped = statusData.stopped || 0;
        const notRunning = statusData.not_running || 0;
        const failed = statusData.failed || 0;
        const completed = stopped + notRunning + failed;
        const remaining = total > 0 ? total - completed : 0;

        return `Stopping '${groupName}': ${completed}/${total} | ` +
            `⏹ ${stopped} stopped, ` +
            `⏸ ${notRunning} not running, ` +
            `✗ ${failed} failed, ` +
            `⏳ ${remaining} remaining`;
    },

    handleGroupOperationComplete(statusData, groupName, operationType) {
        const isStart = operationType === 'start';
        const started = statusData.started || 0;
        const stopped = statusData.stopped || 0;
        const alreadyRunning = statusData.already_running || 0;
        const notRunning = statusData.not_running || 0;
        const failed = statusData.failed || 0;

        let message = `Group '${groupName}' ${isStart ? 'started' : 'stopped'}! `;
        const details = [];

        if (isStart) {
            if (started > 0) details.push(`${started} started`);
            if (alreadyRunning > 0) details.push(`${alreadyRunning} already running`);
        } else {
            if (stopped > 0) details.push(`${stopped} stopped`);
            if (notRunning > 0) details.push(`${notRunning} were not running`);
        }

        if (failed > 0) details.push(`${failed} failed`);

        message += details.join(', ');

        const toastType = failed > 0 ? 'warning' : 'success';
        ToastManager.show(message, toastType);

        if (failed > 0 && statusData.errors) {
            ToastManager.showErrorsSequentially(statusData.errors, `Errors in group '${groupName}':`);
        }

        setTimeout(() => location.reload(), isStart ? 5000 : 2000);
    }
};

// =========================================================
// Bulk Operations
// =========================================================
const BulkOperations = {
    async stopAllRunning() {
        try {
            const confirmed = await showConfirmModal(
                'Stop All Containers',
                'Are you sure you want to stop ALL running containers? This will gracefully stop all running playground containers.',
                'danger'
            );
            if (!confirmed) return;

            showLoader('Initiating stop all operation...');
            ToastManager.show('Initiating stop all operation...', 'info');

            const { controller, timeoutId } = Utils.createAbortController(Constants.POLLING.TIMEOUT.STOP);

            try {
                const response = await fetch('/api/stop-all', {
                    method: 'POST',
                    signal: controller.signal
                });
                Utils.clearAbortTimeout(timeoutId);

                const data = await response.json();

                if (response.ok) {
                    ToastManager.show(`Stop operation started. ID: ${data.operation_id}`, 'info');
                    this.pollStopAllStatus(data.operation_id);
                } else {
                    ToastManager.show(`Failed to start stop operation: ${data.error || response.statusText}`, 'error');
                    hideLoader();
                }
            } catch (fetchError) {
                Utils.clearAbortTimeout(timeoutId);
                if (fetchError.name === 'AbortError') {
                    ToastManager.show('Operation request timed out - please check server status', 'warning');
                } else {
                    ToastManager.show(`Error: ${fetchError.message}`, 'error');
                }
                hideLoader();
            }
        } catch (error) {
            ToastManager.show(`Error: ${error.message}`, 'error');
            hideLoader();
        }
    },

    async pollStopAllStatus(operationId) {
        let attempts = 0;

        showLoader('Stopping containers: Awaiting progress...');

        const poll = async () => {
            try {
                const response = await fetch(`/api/operation-status/${operationId}`);
                const statusData = await response.json();

                const total = statusData.total || '?';
                const stopped = statusData.stopped || 0;
                showLoader(`Stopping containers: ${stopped} of ${total} | Status: ${statusData.status}`);

                if (statusData.status === 'completed') {
                    ToastManager.show(`Stopped ${stopped} containers successfully!`, 'success');
                    hideLoader();

                    setTimeout(() => {
                        location.reload();
                    }, Constants.TOAST.DELAY_BEFORE_RELOAD);
                    return;
                }

                if (statusData.status === 'error') {
                    ToastManager.show(`Stop operation failed: ${statusData.error}`, 'error');
                    hideLoader();
                    return;
                }

                attempts++;
                if (attempts < Constants.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Constants.POLLING.INTERVAL);
                } else {
                    ToastManager.show(`Operation timed out after ${Constants.POLLING.MAX_ATTEMPTS} attempts. Please check the 'Manage' page or refresh manually.`, 'warning');
                    hideLoader();
                }

            } catch (error) {
                console.error('Polling error:', error);
                ToastManager.show('An error occurred during status check.', 'error');
                hideLoader();
            }
        };

        poll();
    }
};

// =========================================================
// Container Tag Management
// =========================================================
const ContainerTagManager = {
    init() {
        this.initializeContainerTagHandlers();
        this.refreshContainerTagStatuses();
    },

    initializeContainerTagHandlers() {
        const containerTags = document.querySelectorAll('.container-tag');

        containerTags.forEach(tag => {
            const containerName = tag.getAttribute('data-container');

            if (containerName) {
                tag.addEventListener('click', (e) => {
                    e.stopPropagation();
                    FilterManager.quickSearchContainer(containerName);
                });

                tag.style.cursor = 'pointer';
                tag.title = `Click to filter by ${containerName}`;
                this.updateContainerTagStatus(tag, containerName);
            }
        });
    },

    updateContainerTagStatus(tag, containerName) {
        const statusDot = tag.querySelector('.container-status-dot');
        const matchingCard = document.querySelector(`.image-card[data-name="${containerName}"]`);

        if (statusDot && matchingCard) {
            const statusText = matchingCard.querySelector('.status-text');
            if (statusText) {
                const isRunning = statusText.textContent.toLowerCase() === 'running';

                if (isRunning) {
                    statusDot.style.background = '#10b981';
                    statusDot.style.animation = 'pulse 2s ease-in-out infinite';
                    tag.setAttribute('data-running', 'true');
                } else {
                    statusDot.style.background = '#94a3b8';
                    statusDot.style.animation = 'none';
                    tag.setAttribute('data-running', 'false');
                }
            }
        }
    },

    refreshContainerTagStatuses() {
        const containerTags = document.querySelectorAll('.container-tag');
        containerTags.forEach(tag => {
            const containerName = tag.getAttribute('data-container');
            if (containerName) {
                this.updateContainerTagStatus(tag, containerName);
            }
        });
    }
};

// =========================================================
// Event Listeners & Initialization
// =========================================================
function initializeEventListeners() {
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (document.getElementById('consoleModal')?.classList.contains('modal-open')) {
                ConsoleManager.close();
            } else if (document.getElementById('logModal')?.classList.contains('modal-open')) {
                closeModal('logModal');
            }
        }
        if (e.ctrlKey && e.key === 'k') {
            e.preventDefault();
            if (DOM.filterInput) DOM.filterInput.focus();
        }
    });

    // Initialize container tags
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            ContainerTagManager.init();
        });
    } else {
        ContainerTagManager.init();
    }
}

// =========================================================
// Modal Management
// =========================================================
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

// =========================================================
// Loader Management
// =========================================================
const LoaderManager = {
    show(message = 'Please wait...') {
        const loader = document.getElementById('global-loader');
        const messageElement = document.getElementById('loader-message');

        if (messageElement) {
            messageElement.textContent = message;
        }

        if (loader) {
            // USA 'active' INVECE DI RIMUOVERE 'hidden'
            loader.classList.add('active');
            document.body.style.overflow = 'hidden';
        } else {
            console.error('Loader element not found!');
            ToastManager.show(`Operation in progress: ${message}`, 'info');
        }
    },

    hide() {
        const loader = document.getElementById('global-loader');
        if (loader) {
            // RIMUOVI 'active' INVECE DI AGGIUNGERE 'hidden'
            loader.classList.remove('active');
            document.body.style.overflow = '';
        } else {
            console.error('Loader element not found!');
        }
    }
};

// =========================================================
// Confirm Modal Management
// =========================================================
const ConfirmModalManager = {
    async show(title, message, type = 'warning') {
        return new Promise((resolve) => {
            const modal = document.getElementById('confirmModal');
            const icons = {
                danger: '⚠',
                warning: '⚠',
                info: 'ℹ',
                success: '✓'
            };

            modal.innerHTML = `
                <div class="modal-overlay" onclick="ConfirmModalManager.hide(false)"></div>
                <div class="modal-content modal-small">
                    <div class="modal-header">
                        <h2>${icons[type]} ${title}</h2>
                        <button class="modal-close" onclick="ConfirmModalManager.hide(false)">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="confirm-message">${message}</div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="ConfirmModalManager.hide(false)">
                            Cancel
                        </button>
                        <button class="btn btn-${type}" onclick="ConfirmModalManager.hide(true)">
                            Confirm
                        </button>
                    </div>
                </div>
            `;

            this.resolvePromise = resolve;
            ModalManager.open('confirmModal');
        });
    },

    hide(confirmed) {
        ModalManager.close('confirmModal');
        if (this.resolvePromise) {
            this.resolvePromise(confirmed);
            this.resolvePromise = null;
        }
    }
};

// =========================================================
// Logs Management
// =========================================================
const LogsManager = {
    currentContainer: null,
    refreshInterval: null,
    isFollowing: false,
    refreshRate: 2000, // 2 secondi

    async show(container, follow = false) {
        try {
            this.currentContainer = container;
            const response = await fetch(`/logs/${container}`);
            const data = await response.json();

            document.getElementById('logContainerName').textContent = container;
            document.getElementById('logContent').textContent = data.logs || 'No logs available';
            
            // Aggiungi controlli per il follow
            this.addFollowControls();
            
            ModalManager.open('logModal');
            
            // Se richiesto, avvia il follow
            if (follow) {
                this.startFollowing();
            }
        } catch (error) {
            ToastManager.show(`Error loading logs: ${error.message}`, 'error');
        }
    },

    addFollowControls() {
    // Crea o aggiorna i controlli nel modal
    let controls = document.getElementById('logFollowControls');
    if (!controls) {
        controls = document.createElement('div');
        controls.id = 'logFollowControls';
        controls.className = 'log-controls';
        controls.innerHTML = `
            <button id="followToggleBtn" class="btn btn-sm">
                <span class="follow-icon">▶</span> Following log
            </button>
            <button id="refreshLogBtn" class="btn btn-sm hidden">
                🔄 Refresh
            </button>
            <span id="followStatus" class="status-indicator"></span>
        `;
        
        const logHeader = document.querySelector('#logModal .modal-header');
        const closeButton = logHeader.querySelector('.btn-close'); // Seleziona il pulsante di chiusura
        
        if (closeButton) {
            // Inserisci i controlli prima del pulsante di chiusura
            logHeader.insertBefore(controls, closeButton);
        } else {
            // Se non c'è il pulsante di chiusura, aggiungi i controlli come ultimo elemento
            logHeader.appendChild(controls);
        }
        
        // Aggiungi event listeners
        document.getElementById('followToggleBtn').addEventListener('click', () => {
            this.toggleFollow();
        });
        
        document.getElementById('refreshLogBtn').addEventListener('click', () => {
            this.refreshLogs();
        });
    }
    
    this.updateFollowButton();
},

    async refreshLogs() {
        if (!this.currentContainer) return;
        
        try {
            const response = await fetch(`/logs/${this.currentContainer}?t=${Date.now()}`);
            const data = await response.json();
            
            const logContent = document.getElementById('logContent');
            logContent.textContent = data.logs || 'No logs available';
            
            // Se stiamo seguendo, scrolla in fondo
            if (this.isFollowing) {
                logContent.scrollTop = logContent.scrollHeight;
            }
            
            this.updateFollowStatus('Ultimo aggiornamento: ' + new Date().toLocaleTimeString());
        } catch (error) {
            ToastManager.show(`Error refreshing logs: ${error.message}`, 'error');
            this.stopFollowing();
        }
    },

    toggleFollow() {
        if (this.isFollowing) {
            this.stopFollowing();
        } else {
            this.startFollowing();
        }
    },

    startFollowing() {
        this.isFollowing = true;
        this.refreshInterval = setInterval(() => {
            this.refreshLogs();
        }, this.refreshRate);
        
        this.updateFollowButton();
        this.updateFollowStatus('Seguendo i log...');
        
        // Scrolla immediatamente in fondo
        const logContent = document.getElementById('logContent');
        logContent.scrollTop = logContent.scrollHeight;
    },

    stopFollowing() {
        this.isFollowing = false;
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        
        this.updateFollowButton();
        this.updateFollowStatus('Pausa');
    },

    updateFollowButton() {
        const btn = document.getElementById('followToggleBtn');
        const icon = btn.querySelector('.follow-icon');
        if (btn) {
            if (this.isFollowing) {
                btn.classList.add('active');
                icon.textContent = '⏸';
                btn.innerHTML = btn.innerHTML.replace('Segui log', 'Pausa');
            } else {
                btn.classList.remove('active');
                icon.textContent = '▶';
                btn.innerHTML = btn.innerHTML.replace('Pausa', 'Segui log');
            }
        }
    },

    updateFollowStatus(message) {
        const status = document.getElementById('followStatus');
        if (status) {
            status.textContent = message;
        }
    },

    close() {
        this.stopFollowing();
        this.currentContainer = null;
        ModalManager.close('logModal');
    },

    // Metodo per cambiare la frequenza di aggiornamento
    setRefreshRate(rate) {
        this.refreshRate = rate;
        if (this.isFollowing) {
            this.stopFollowing();
            this.startFollowing();
        }
    }
};

// =========================================================
// Global Export (for HTML onclick handlers)
// =========================================================
window.ContainerManager = ContainerManager;
window.ConsoleManager = ConsoleManager;
window.GroupManager = GroupManager;
window.BulkOperations = BulkOperations;
window.FilterManager = FilterManager;
window.LogsManager = LogsManager;

// Funzioni globali per compatibilità con l'HTML esistente
window.showLogs = LogsManager.show.bind(LogsManager);
window.closeModal = ModalManager.close.bind(ModalManager);
window.openModal = ModalManager.open.bind(ModalManager);
window.showConfirmModal = ConfirmModalManager.show.bind(ConfirmModalManager);
window.showLoader = LoaderManager.show.bind(LoaderManager);
window.hideLoader = LoaderManager.hide.bind(LoaderManager);

// Initialize the application
initializeEventListeners();
FilterManager.init();