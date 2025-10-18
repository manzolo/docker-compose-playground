// =========================================================
// MANAGER OPERATIONS - Advanced Manager page operations
// =========================================================

const ManagerOperations = {
    /**
     * Stop all containers
     */
    async stopAll() {
        try {
            const confirmed = await showConfirmModal(
                'Stop All Containers',
                'Are you sure you want to stop ALL running containers?',
                'danger'
            );
            if (!confirmed) return;

            showLoader('Stopping all containers...');
            const data = await ApiService.stopAll();

            if (data.operation_id) {
                ToastManager.show('Stop operation started...', 'info');
                this.pollOperation(data.operation_id, 'stop', 'Stopping');
            }
        } catch (error) {
            this.handleError(error, 'stop');
        }
    },

    /**
     * Restart all containers
     */
    async restartAll() {
        try {
            const confirmed = await showConfirmModal(
                'Restart All Containers',
                'Are you sure you want to restart ALL running containers?',
                'warning'
            );
            if (!confirmed) return;

            showLoader('Restarting all containers...');
            const data = await ApiService.restartAll();

            if (data.operation_id) {
                ToastManager.show('Restart operation started...', 'info');
                this.pollOperation(data.operation_id, 'restart', 'Restarting');
            }
        } catch (error) {
            this.handleError(error, 'restart');
        }
    },

    /**
     * Cleanup all containers
     */
    async cleanupAll() {
        try {
            const confirmed = await showConfirmModal(
                'Cleanup All Containers',
                '⚠ DANGER: This will STOP and REMOVE ALL playground containers! Are you absolutely sure?',
                'danger'
            );
            if (!confirmed) return;

            const doubleCheck = await showConfirmModal(
                'Final Confirmation',
                'This action cannot be undone. Are you sure you want to proceed?',
                'danger'
            );
            if (!doubleCheck) return;

            showLoader('Cleaning up all containers...');
            const data = await ApiService.cleanupAll();

            if (data.operation_id) {
                ToastManager.show('Cleanup operation started...', 'warning');
                this.pollOperation(data.operation_id, 'cleanup', 'Cleaning up');
            }
        } catch (error) {
            this.handleError(error, 'cleanup');
        }
    },

    /**
     * Poll operation status
     */
    async pollOperation(operationId, operationType, verbName) {
        let attempts = 0;

        const poll = async () => {
            try {
                const statusData = await ApiService.getOperationStatus(operationId);
                const total = statusData.total || '?';
                const count = statusData[this.getCountField(operationType)] || 0;

                showLoader(`${verbName} containers: ${count} of ${total}`);

                if (statusData.status === 'completed') {
                    ToastManager.show(`${verbName} operation completed!`, 'success');
                    hideLoader();
                    setTimeout(() => location.reload(), 2500);
                    return;
                }

                if (statusData.status === 'error') {
                    ToastManager.show(`${verbName} operation failed: ${statusData.error}`, 'error');
                    hideLoader();
                    return;
                }

                attempts++;
                if (attempts < Config.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Config.POLLING.INTERVAL);
                } else {
                    ToastManager.show('Operation timed out. Please check manually.', 'warning');
                    hideLoader();
                }
            } catch (error) {
                console.error('Polling error:', error);
                attempts++;
                if (attempts < Config.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Config.POLLING.INTERVAL);
                } else {
                    ToastManager.show('Polling failed after maximum attempts.', 'error');
                    hideLoader();
                }
            }
        };

        poll();
    },

    /**
     * Get count field for operation type
     */
    getCountField(operationType) {
        const fields = {
            stop: 'stopped',
            restart: 'restarted',
            cleanup: 'removed'
        };
        return fields[operationType] || 'completed';
    },

    /**
     * Handle operation error
     */
    handleError(error, operationType) {
        if (error.name === 'AbortError') {
            ToastManager.show('Operation request timed out', 'warning');
        } else {
            ToastManager.show(`${operationType} operation failed: ${error.message}`, 'error');
        }
        hideLoader();
    }
};

// =========================================================
// CATEGORY OPERATIONS - Start/stop by category
// =========================================================

const CategoryOperations = {
    /**
     * Start by category
     */
    async startByCategory() {
        try {
            const category = await this.showCategoryInput(
                'Start Category',
                'Enter the category name to start all its containers:',
                'e.g., linux, database, programming...'
            );
            if (!category) return;

            await this.performCategoryOperation(category, 'start');
        } catch (error) {
            this.handleCategoryError(error, 'start');
        }
    },

    /**
     * Start specific category
     */
    async startCategory(category) {
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
    },

    /**
     * Perform category operation
     */
    async performCategoryOperation(category, operation) {
        showLoader(`${operation === 'start' ? 'Starting' : 'Stopping'} containers in category ${category}...`);
        ToastManager.show(`${operation === 'start' ? 'Starting' : 'Stopping'} ${category} containers...`, 'info');

        try {
            const data = operation === 'start' 
                ? await ApiService.startCategory(category)
                : await ApiService.stopCategory(category);

            if (data.started > 0 || data.stopped > 0) {
                const count = data.started || data.stopped;
                ToastManager.show(
                    `Successfully ${operation === 'start' ? 'started' : 'stopped'} ${count} containers`,
                    'success'
                );
            } else {
                ToastManager.show(
                    `No containers ${operation === 'start' ? 'started' : 'stopped'} in category: ${category}`,
                    'warning'
                );
            }

            hideLoader();
            setTimeout(() => location.reload(), 2000);
        } catch (error) {
            this.handleCategoryError(error, operation);
        }
    },

    /**
     * Show category input modal
     */
    async showCategoryInput(title, message, placeholder) {
        return new Promise((resolve) => {
            const modal = DOM.get('confirmModal');

            modal.innerHTML = `
                <div class="modal-overlay"></div>
                <div class="modal-content">
                    <div class="confirm-modal-header">
                        <h2><span class="confirm-modal-icon">🏷</span> ${title}</h2>
                    </div>
                    <div class="confirm-modal-body">
                        <p class="confirm-modal-message">${message}</p>
                        <label class="input-label">
                            Category Name
                            <input 
                                type="text" 
                                id="categoryInput" 
                                class="confirm-input" 
                                placeholder="${placeholder}"
                                autocomplete="off"
                            />
                        </label>
                    </div>
                    <div class="confirm-modal-footer">
                        <button class="btn btn-confirm-cancel" id="categoryCancel">Cancel</button>
                        <button class="btn btn-confirm-primary" id="categoryConfirm">Confirm</button>
                    </div>
                </div>
            `;

            const input = DOM.get('categoryInput');
            const confirmBtn = DOM.get('categoryConfirm');
            const cancelBtn = DOM.get('categoryCancel');
            const overlay = modal.querySelector('.modal-overlay');

            ModalManager.open('confirmModal');
            setTimeout(() => input.focus(), 100);

            const cleanup = () => {
                ModalManager.close('confirmModal');
                confirmBtn.removeEventListener('click', onConfirm);
                cancelBtn.removeEventListener('click', onCancel);
                overlay.removeEventListener('click', onCancel);
                input.removeEventListener('keydown', onKeyDown);
            };

            const onConfirm = () => {
                const value = input.value.trim();
                cleanup();
                resolve(value || null);
            };

            const onCancel = () => {
                cleanup();
                resolve(null);
            };

            const onKeyDown = (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    onConfirm();
                } else if (e.key === 'Escape') {
                    onCancel();
                }
            };

            confirmBtn.addEventListener('click', onConfirm);
            cancelBtn.addEventListener('click', onCancel);
            overlay.addEventListener('click', onCancel);
            input.addEventListener('keydown', onKeyDown);
        });
    },

    /**
     * Handle category error
     */
    handleCategoryError(error, operation) {
        if (error.name === 'AbortError') {
            ToastManager.show('Operation timeout - please wait and refresh manually', 'warning');
            hideLoader();
            setTimeout(() => location.reload(), 5000);
        } else {
            ToastManager.show(`${operation} operation failed: ${error.message}`, 'error');
            hideLoader();
        }
    }
};

window.ManagerOperations = ManagerOperations;
window.CategoryOperations = CategoryOperations;