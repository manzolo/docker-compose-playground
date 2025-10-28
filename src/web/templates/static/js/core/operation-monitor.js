// =========================================================
// OPERATION MONITOR - Persistent widget for background operations
// =========================================================

const OperationMonitor = {
    activeOperations: {},
    pollTimeouts: {}, // Track timeouts per operation per cleanup

    /**
     * Start monitoring an operation with persistent widget
     */
    startMonitoring(operationId, operationName = 'Operation') {
        // Evita duplicati
        if (this.activeOperations[operationId]) {
            console.warn(`Operation ${operationId} already being monitored`);
            return;
        }

        // Crea widget se non esiste
        if (!DOM.get('operation-monitor-container')) {
            this.createMonitorContainer();
        }

        // Aggiungi operazione al tracking
        this.activeOperations[operationId] = {
            name: operationName,
            startTime: new Date(),
            status: 'running'
        };

        // Crea card per l'operazione
        this.createOperationCard(operationId, operationName);

        // Inizia il polling
        this.pollOperation(operationId);
    },

    /**
     * Create main monitor container
     */
    createMonitorContainer() {
        const container = document.createElement('div');
        container.id = 'operation-monitor-container';
        container.className = 'operation-monitor-container';
        document.body.appendChild(container);
    },

    /**
     * Create card for operation
     */
    createOperationCard(operationId, operationName) {
        const container = DOM.get('operation-monitor-container');
        if (!container) return;

        const card = document.createElement('div');
        card.id = `operation-${operationId}`;
        card.className = 'operation-card operation-running';
        card.innerHTML = `
            <div class="operation-header">
                <div class="operation-title">
                    <span class="operation-icon">⏳</span>
                    <span class="operation-name">${operationName}</span>
                </div>
                <button class="operation-close" onclick="OperationMonitor.closeOperation('${operationId}')">×</button>
            </div>
            <div class="operation-content">
                <div class="operation-message" id="message-${operationId}">Inizializzazione...</div>
                <div class="operation-progress" id="progress-${operationId}"></div>
            </div>
        `;
        container.appendChild(card);
    },

    /**
     * Poll operation status - with proper cleanup
     */
    async pollOperation(operationId) {
        let attempts = 0;
        const maxAttempts = 1800;

        const poll = async () => {
            try {
                const statusData = await fetch(`/api/operation-status/${operationId}`)
                    .then(r => r.json());

                // Aggiorna card
                this.updateOperationCard(operationId, statusData);

                if (statusData.status === 'completed') {
                    this.completeOperation(operationId, statusData);
                    return;
                }

                if (statusData.status === 'error') {
                    this.failOperation(operationId, statusData);
                    return;
                }

                // Continua il polling
                attempts++;
                if (attempts < maxAttempts) {
                    const timeoutId = setTimeout(poll, 1000);
                    // Traccia il timeout per cleanup
                    this.pollTimeouts[`${operationId}_${attempts}`] = timeoutId;
                } else {
                    this.timeoutOperation(operationId);
                }
            } catch (error) {
                console.error('Polling error:', error);
                attempts++;
                if (attempts < maxAttempts) {
                    const timeoutId = setTimeout(poll, 1000);
                    this.pollTimeouts[`${operationId}_${attempts}`] = timeoutId;
                } else {
                    this.timeoutOperation(operationId);
                }
            }
        };

        poll();
    },

    /**
     * Update operation card
     */
    updateOperationCard(operationId, statusData) {
        const card = DOM.get(`operation-${operationId}`);
        if (!card) return;

        const messageEl = DOM.get(`message-${operationId}`);
        if (messageEl) {
            messageEl.textContent = this.formatOperationMessage(statusData);
        }
    },

    /**
     * Format operation message with proper line breaks
     */
    formatOperationMessage(statusData) {
        const total = statusData.total || '?';
        const operation = statusData.operation || 'unknown';
        const elapsed = this.getElapsedTime(statusData.started_at);

        let message = '';

        if (operation === 'start_group' || operation === 'start') {
            const started = statusData.started || 0;
            const alreadyRunning = statusData.already_running || 0;
            const failed = statusData.failed || 0;
            const completed = started + alreadyRunning + failed;
            const remaining = total !== '?' ? total - completed : '?';

            message = `Starting: ${completed}/${total} (${elapsed})\n`;
            message += `✅ ${started} started \n⚡ ${alreadyRunning} running \n❌ ${failed} failed \n⏳ ${remaining} remaining`;

            const scriptStatus = Utils.formatScriptStatus(statusData);
            if (scriptStatus) {
                message += `\n${scriptStatus}`;
            }
        } else if (operation === 'stop_group' || operation === 'stop' || operation === 'stop_all') {
            const stopped = statusData.stopped || 0;
            const notRunning = statusData.not_running || 0;
            const failed = statusData.failed || 0;
            const completed = stopped + notRunning + failed;
            const remaining = total !== '?' ? total - completed : '?';

            message = `Stopping: ${completed}/${total} (${elapsed})\n`;
            message += `🛑 ${stopped} stopped \n🚫 ${notRunning} not running \n❌ ${failed} failed \n⏳ ${remaining} remaining`;

            const scriptStatus = Utils.formatScriptStatus(statusData);
            if (scriptStatus) {
                message += `\n${scriptStatus}`;
            }
        } else if (operation === 'restart_all' || operation === 'restart') {
            const restarted = statusData.restarted || 0;
            const failed = statusData.failed || 0;
            const completed = restarted + failed;
            const remaining = total !== '?' ? total - completed : '?';

            message = `Restarting: ${completed}/${total} (${elapsed})\n`;
            message += `🔄 ${restarted} restarted | ✗ ${failed} failed | ⏳ ${remaining} remaining`;

            const scriptStatus = Utils.formatScriptStatus(statusData);
            if (scriptStatus) {
                message += `\n${scriptStatus}`;
            }
        } else if (operation === 'cleanup') {
            const removed = statusData.removed || 0;
            const failed = statusData.failed || 0;
            const completed = removed + failed;
            const remaining = total !== '?' ? total - completed : '?';

            message = `Cleaning up: ${completed}/${total} (${elapsed})\n`;
            message += `🗑️ ${removed} removed | ✗ ${failed} failed | ⏳ ${remaining} remaining`;

            const scriptStatus = Utils.formatScriptStatus(statusData);
            if (scriptStatus) {
                message += `\n${scriptStatus}`;
            }
        }

        return message;
    },

    /**
     * Calculate elapsed time from ISO timestamp
     */
    getElapsedTime(startedAt) {
        try {
            if (!startedAt) return '0s';

            const start = new Date(startedAt);
            const now = new Date();
            const seconds = Math.floor((now - start) / 1000);

            if (seconds < 60) return `${seconds}s`;
            const minutes = Math.floor(seconds / 60);
            const remainingSecs = seconds % 60;
            return `${minutes}m ${remainingSecs}s`;
        } catch (e) {
            return '--';
        }
    },

    /**
     * Complete operation - CHIUDE IL LOADER
     */
    completeOperation(operationId, statusData) {
        const card = DOM.get(`operation-${operationId}`);
        if (!card) return;

        hideLoader();
        DOM.removeClass(card, 'operation-running');
        DOM.addClass(card, 'operation-completed');

        const header = card.querySelector('.operation-header');
        const icon = header.querySelector('.operation-icon');
        icon.textContent = '✓';

        const messageEl = card.querySelector('.operation-message');
        const operationName = this.activeOperations[operationId]?.name || 'Operation';

        // Verifica se l'operazione è un'operazione di gruppo
        if (operationName.startsWith('Group:') || operationName.startsWith('Stopping Group:')) {
            const groupName = operationName.replace(/^Group: |^Stopping Group: /, '');
            const operationType = operationName.startsWith('Group:') ? 'start' : 'stop';
            GroupOperations.handleGroupOperationComplete(statusData, groupName, operationType);
        } else {
            messageEl.textContent = 'Operation completed!';
        }

        this.activeOperations[operationId].status = 'completed';

        // Pulisci timeouts
        this.cleanupPollTimeouts(operationId);

        // Auto-chiudi dopo 5 secondi
        setTimeout(() => {
            this.closeOperation(operationId);
            ReloadManager.showReloadToast(7000);
        }, 5000);
    },

    /**
     * Fail operation - CHIUDE IL LOADER
     */
    failOperation(operationId, statusData) {
        const card = DOM.get(`operation-${operationId}`);
        if (!card) return;

        hideLoader();
        DOM.removeClass(card, 'operation-running');
        DOM.addClass(card, 'operation-failed');

        const header = card.querySelector('.operation-header');
        const icon = header.querySelector('.operation-icon');
        icon.textContent = '✗';

        const messageEl = card.querySelector('.operation-message');
        messageEl.textContent = `Errore: ${statusData.error || 'Operazione fallita'}`;

        this.activeOperations[operationId].status = 'failed';

        // Pulisci timeouts
        this.cleanupPollTimeouts(operationId);

        ToastManager.show(`Task failed: ${statusData.error || 'Unknown'}`, 'error');
    },

    /**
     * Timeout operation - CHIUDE IL LOADER
     */
    timeoutOperation(operationId) {
        const card = DOM.get(`operation-${operationId}`);
        if (!card) return;

        hideLoader();
        DOM.removeClass(card, 'operation-running');
        DOM.addClass(card, 'operation-timeout');

        const header = card.querySelector('.operation-header');
        const icon = header.querySelector('.operation-icon');
        icon.textContent = '⏱';

        const messageEl = card.querySelector('.operation-message');
        messageEl.textContent = 'Timeout: The operation continues in the background. Reload the page to check the status.';

        this.activeOperations[operationId].status = 'timeout';

        // Pulisci timeouts
        this.cleanupPollTimeouts(operationId);

        ToastManager.show('Operation timed out - continues in background', 'warning');
    },

    /**
     * Close operation card with animation
     */
    closeOperation(operationId) {
        const card = DOM.get(`operation-${operationId}`);
        if (card) {
            card.classList.add('operation-closing');
            setTimeout(() => {
                if (card.parentElement) {
                    card.remove();
                }
            }, 300);
        }

        // Pulisci tracciamento
        delete this.activeOperations[operationId];
        this.cleanupPollTimeouts(operationId);

        // Cleanup di sicurezza
        if (OperationHelper) {
            OperationHelper.cleanup();
        }
    },

    /**
     * Cleanup poll timeouts per operazione
     */
    cleanupPollTimeouts(operationId) {
        const keys = Object.keys(this.pollTimeouts);
        keys.forEach(key => {
            if (key.startsWith(`${operationId}_`)) {
                clearTimeout(this.pollTimeouts[key]);
                delete this.pollTimeouts[key];
            }
        });
    },

    /**
     * Cleanup globale (per beforeunload)
     */
    cleanup() {
        // Chiudi tutti i poll timeouts
        Object.values(this.pollTimeouts).forEach(timeoutId => {
            clearTimeout(timeoutId);
        });
        this.pollTimeouts = {};

        // Chiudi tutte le operazioni
        Object.keys(this.activeOperations).forEach(operationId => {
            this.closeOperation(operationId);
        });
    }
};

window.OperationMonitor = OperationMonitor;

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    OperationMonitor.cleanup();
});