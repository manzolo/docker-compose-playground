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
    currentButton: null,
    currentButtonOriginalHTML: null,

    /**
     * Start a group
     */
    async startGroup(groupName) {
        // Find the group card and start button
        const groupCard = DOM.query(`[data-group="${groupName}"]`);
        const startBtn = groupCard?.querySelector('.group-start-btn');

        try {
            const confirmed = await showConfirmModal(
                'Start Application Stack',
                `Start all containers in <strong>${groupName}</strong>?`,
                'success'
            );
            if (!confirmed) return;

            // Show loading spinner on button
            if (startBtn) {
                this.currentButton = startBtn;
                this.currentButtonOriginalHTML = startBtn.innerHTML;
                startBtn.disabled = true;
                startBtn.innerHTML = '<span>⏳</span>';
            }

            const response = await ApiService.startGroup(groupName);

            if (response.operation_id) {
                OperationMonitor.startMonitoring(response.operation_id, `Group: ${groupName}`);
            } else {
                throw new Error('No operation ID received');
            }

        } catch (error) {
            hideLoader();
            this.restoreButton();
            this.handleGroupOperationError(error, 'start');
        }
    },

    /**
     * Stop a group
     */
    async stopGroup(groupName) {
        // Find the group card and stop button
        const groupCard = DOM.query(`[data-group="${groupName}"]`);
        const stopBtn = groupCard?.querySelector('.group-stop-btn');

        try {
            const confirmed = await showConfirmModal(
                'Stop Application Stack',
                `Stop all containers in <strong>${groupName}</strong>?`,
                'warning'
            );
            if (!confirmed) return;

            // Show loading spinner on button
            if (stopBtn) {
                this.currentButton = stopBtn;
                this.currentButtonOriginalHTML = stopBtn.innerHTML;
                stopBtn.disabled = true;
                stopBtn.innerHTML = '<span>⏳</span>';
            }

            const response = await ApiService.stopGroup(groupName);

            if (response.operation_id) {
                OperationMonitor.startMonitoring(response.operation_id, `Stopping Group: ${groupName}`);
            } else {
                throw new Error('No operation ID received');
            }

        } catch (error) {
            hideLoader();
            this.restoreButton();
            this.handleGroupOperationError(error, 'stop');
        }
    },

    /**
     * Handle group operation completion
     */
    async handleGroupOperationComplete(statusData, groupName, operationType) {
        // Restore button state
        this.restoreButton();

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

        if (failed > 0 && statusData.errors && Array.isArray(statusData.errors)) {
            ToastManager.showErrorsSequentially(statusData.errors, `Errors in group '${groupName}':`);
        }

        // Refresh all container cards in the group without page reload
        await this.refreshGroupContainers(statusData, isStart);
    },

    /**
     * Refresh all container cards in a group
     */
    async refreshGroupContainers(statusData, isStart) {
        // Get list of containers that were affected
        const containers = statusData.containers || [];

        if (containers.length === 0) return;

        // Refresh each container card
        const refreshPromises = containers.map(containerName => {
            if (window.ContainerManager && typeof ContainerManager.refreshCardState === 'function') {
                return ContainerManager.refreshCardState(containerName);
            }
            return Promise.resolve();
        });

        try {
            await Promise.all(refreshPromises);
            // console.log(`Refreshed ${containers.length} container cards after group operation`);

            // Update counters after all cards have been refreshed
            if (window.FilterManager && typeof FilterManager.updateCounts === 'function') {
                FilterManager.updateCounts();
            }

            // Update container tag statuses in group cards
            if (window.ContainerTagManager && typeof ContainerTagManager.refreshContainerTagStatuses === 'function') {
                ContainerTagManager.refreshContainerTagStatuses();
            }
        } catch (error) {
            console.error('Error refreshing group containers:', error);
        }
    },

    /**
     * Restore button to original state
     */
    restoreButton() {
        if (this.currentButton && this.currentButtonOriginalHTML) {
            this.currentButton.disabled = false;
            this.currentButton.innerHTML = this.currentButtonOriginalHTML;
            this.currentButton = null;
            this.currentButtonOriginalHTML = null;
        }
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
    }
};

window.GroupManager = GroupManager;
window.GroupOperations = GroupOperations;
window.GroupPersistenceManager = GroupPersistenceManager;
window.toggleGroup = (headerElement) => GroupManager.toggleGroup(headerElement);