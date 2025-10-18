// =========================================================
// GROUP MANAGER - Application stacks operations
// =========================================================

const GroupManager = {
    /**
     * Toggle group collapse/expand
     */
    toggleGroup(headerElement) {
        const content = headerElement.nextElementSibling;
        const icon = headerElement.querySelector('.group-toggle-icon');
        const card = headerElement.closest('.group-card');
        const groupName = card?.getAttribute('data-group');

        if (!groupName) return;

        const isCollapsed = DOM.toggleClass(content, 'collapsed');
        DOM.toggleClass(icon, 'collapsed');

        GroupPersistenceManager.saveGroupStates();
    },

    /**
     * Filter groups by search and category
     */
    filterGroups(searchTerm, selectedCategory) {
        DOM.queryAll('.group-card').forEach(card => {
            const groupName = card.getAttribute('data-group').toLowerCase();
            const searchData = card.getAttribute('data-search').toLowerCase();
            const categoryElement = card.querySelector('.badge:not(.group-status-badge)');
            const category = categoryElement ? categoryElement.textContent.toLowerCase() : '';

            const matchesSearch = !searchTerm ||
                groupName.includes(searchTerm) ||
                searchData.includes(searchTerm);

            const matchesCategory = !selectedCategory ||
                category === selectedCategory;

            card.style.display = (matchesSearch && matchesCategory) ? '' : 'none';
        });
    }
};

// =========================================================
// GROUP PERSISTENCE MANAGER - Save/restore group states
// =========================================================

const GroupPersistenceManager = {
    /**
     * Save group collapse states
     */
    saveGroupStates() {
        const groupStates = {};
        DOM.queryAll('.group-card').forEach(card => {
            const groupName = card.getAttribute('data-group');
            const content = card.querySelector('.group-card-content');
            const isCollapsed = DOM.hasClass(content, 'collapsed');
            groupStates[groupName] = !isCollapsed;
        });
        sessionStorage.setItem('groupStates', JSON.stringify(groupStates));
    },

    /**
     * Restore group collapse states
     */
    restoreGroupStates() {
        const saved = sessionStorage.getItem('groupStates');
        if (saved) {
            try {
                const groupStates = JSON.parse(saved);

                DOM.queryAll('.group-card').forEach(card => {
                    const groupName = card.getAttribute('data-group');
                    const shouldBeOpen = groupStates[groupName] !== false;
                    const content = card.querySelector('.group-card-content');
                    const icon = card.querySelector('.group-toggle-icon');

                    if (!shouldBeOpen) {
                        DOM.addClass(content, 'collapsed');
                        DOM.addClass(icon, 'collapsed');
                    }
                });
            } catch (error) {
                console.error('Error restoring group states:', error);
            }
        }
    }
};

// =========================================================
// GROUP OPERATIONS - Start/stop groups
// =========================================================

const GroupOperations = {
    /**
     * Start a group
     */
    async startGroup(groupName) {
        try {
            const confirmed = await showConfirmModal(
                'Start Application Stack',
                `Start all containers in <strong>${groupName}</strong>?`,
                'success'
            );
            if (!confirmed) return;

            showLoader(`Initiating start for group '${groupName}'...`);
            ToastManager.show(`Starting ${groupName}...`, 'info');

            const data = await ApiService.startGroup(groupName);

            if (data.operation_id) {
                this.pollStartGroupStatus(data.operation_id, groupName);
            } else {
                throw new Error('No operation ID received');
            }
        } catch (error) {
            this.handleGroupOperationError(error, 'start');
        }
    },

    /**
     * Stop a group
     */
    async stopGroup(groupName) {
        try {
            const confirmed = await showConfirmModal(
                'Stop Application Stack',
                `Stop all containers in <strong>${groupName}</strong>?`,
                'warning'
            );
            if (!confirmed) return;

            showLoader(`Initiating stop for group '${groupName}'...`);

            const data = await ApiService.stopGroup(groupName);

            if (data.operation_id) {
                this.pollStopGroupStatus(data.operation_id, groupName);
            } else {
                throw new Error('No operation ID received');
            }
        } catch (error) {
            this.handleGroupOperationError(error, 'stop');
        }
    },

    /**
     * Poll start group status
     */
    async pollStartGroupStatus(operationId, groupName) {
        await this.pollGroupStatus(
            operationId,
            groupName,
            'start',
            (statusData) => this.formatStartGroupMessage(statusData, groupName)
        );
    },

    /**
     * Poll stop group status
     */
    async pollStopGroupStatus(operationId, groupName) {
        await this.pollGroupStatus(
            operationId,
            groupName,
            'stop',
            (statusData) => this.formatStopGroupMessage(statusData, groupName)
        );
    },

    /**
     * Generic group status polling
     */
    async pollGroupStatus(operationId, groupName, operationType, messageFormatter) {
        let attempts = 0;

        const poll = async () => {
            try {
                const statusData = await ApiService.getOperationStatus(operationId);

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
                if (attempts < Config.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Config.POLLING.INTERVAL);
                } else {
                    ToastManager.show(`Operation timed out. Please check status manually.`, 'warning');
                    hideLoader();
                }

            } catch (error) {
                console.error('Polling error:', error);
                attempts++;
                if (attempts < Config.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Config.POLLING.INTERVAL);
                } else {
                    ToastManager.show('Polling failed after maximum attempts', 'error');
                    hideLoader();
                }
            }
        };

        poll();
    },

    /**
     * Format start group message
     */
    formatStartGroupMessage(statusData, groupName) {
        const total = statusData.total || '?';
        const started = statusData.started || 0;
        const alreadyRunning = statusData.already_running || 0;
        const failed = statusData.failed || 0;
        const completed = started + alreadyRunning + failed;
        const remaining = total !== '?' ? total - completed : '?';

        return `Starting '${groupName}': ${completed}/${total} | ` +
            `✓ ${started} started, ⚡ ${alreadyRunning} running, ✗ ${failed} failed, ⏳ ${remaining} remaining`;
    },

    /**
     * Format stop group message
     */
    formatStopGroupMessage(statusData, groupName) {
        const total = statusData.total || 0;
        const stopped = statusData.stopped || 0;
        const notRunning = statusData.not_running || 0;
        const failed = statusData.failed || 0;
        const completed = stopped + notRunning + failed;
        const remaining = total > 0 ? total - completed : 0;

        return `Stopping '${groupName}': ${completed}/${total} | ` +
            `⏹ ${stopped} stopped, ⏸ ${notRunning} not running, ✗ ${failed} failed, ⏳ ${remaining} remaining`;
    },

    /**
     * Handle group operation completion
     */
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

        ReloadManager.showReloadToast(isStart ? 7000 : 2000);
    },

    /**
     * Handle group operation error
     */
    handleGroupOperationError(error, operation) {
        if (error.name === 'AbortError') {
            ToastManager.show('Request timed out', 'warning');
        } else {
            ToastManager.show(`${operation} operation failed: ${error.message}`, 'error');
        }
        hideLoader();
    }
};

window.GroupManager = GroupManager;
window.GroupOperations = GroupOperations;
window.GroupPersistenceManager = GroupPersistenceManager;
window.toggleGroup = (headerElement) => GroupManager.toggleGroup(headerElement);