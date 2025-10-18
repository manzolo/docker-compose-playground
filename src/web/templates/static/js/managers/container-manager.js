// =========================================================
// CONTAINER MANAGER - Start, stop, and manage containers
// =========================================================

const ContainerManager = {
    /**
     * Start a container
     */
    async startContainer(image) {
        const card = DOM.query(`[data-name="${image}"]`);
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
            const { controller, timeoutId } = Utils.createAbortController(Config.POLLING.TIMEOUT.START);

            const response = await ApiService.startContainer(image);
            Utils.clearAbortTimeout(timeoutId);

            if (response.operation_id) {
                ToastManager.show(`Starting container ${image}...`, 'info');
                await this.pollContainerStatus(response.operation_id, image, btn, originalHTML);
            } else {
                throw new Error('No operation_id received from server');
            }

        } catch (error) {
            this.handleStartError(error, image, btn, originalHTML);
        }
    },

    /**
     * Poll container status
     */
    async pollContainerStatus(operationId, image, btn, originalHTML) {
        try {
            const statusData = await Utils.pollOperationStatus(
                operationId,
                (data) => this.formatContainerStatusMessage(data, image),
                {
                    maxAttempts: Config.POLLING.MAX_ATTEMPTS,
                    interval: Config.POLLING.INTERVAL
                }
            );

            if (statusData.status === 'completed') {
                const started = statusData.started || 0;
                const alreadyRunning = statusData.already_running || 0;

                if (started > 0) {
                    ToastManager.show(`✓ Container ${image} started successfully!`, 'success');
                } else if (alreadyRunning > 0) {
                    ToastManager.show(`ℹ Container ${image} was already running`, 'info');
                }

                this.updateCardUI(image, true, statusData.container || `playground-${image}`);
                ReloadManager.showReloadToast(Config.TOAST.DELAY_BEFORE_RELOAD);

            } else if (statusData.status === 'error') {
                const errorMsg = statusData.error || 'Unknown error';
                ToastManager.show(`✗ Failed to start ${image}: ${errorMsg}`, 'error');

                if (statusData.errors && statusData.errors.length > 0) {
                    ToastManager.showErrorsSequentially(statusData.errors, `Errors starting ${image}:`);
                }

                Utils.updateButtonState(btn, {
                    disabled: false,
                    originalHTML
                });
            }
        } catch (error) {
            ToastManager.show(`✗ Error polling container status: ${error.message}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML
            });
        }
    },

    /**
     * Format container status message
     */
    formatContainerStatusMessage(statusData, image) {
        const total = statusData.total || 1;
        const started = statusData.started || 0;
        const alreadyRunning = statusData.already_running || 0;
        const failed = statusData.failed || 0;
        const completed = started + alreadyRunning + failed;
        const remaining = total - completed;

        if (statusData.status === 'running') {
            return `Starting '${image}': ${completed}/${total} | ` +
                `✓ ${started} started, ⚡ ${alreadyRunning} already running, ✗ ${failed} failed, ⏳ ${remaining} remaining`;
        } else if (statusData.status === 'completed') {
            return `Container '${image}' started successfully! ✓`;
        } else {
            return `Starting container '${image}'...`;
        }
    },

    /**
     * Handle start error
     */
    handleStartError(error, image, btn, originalHTML) {
        hideLoader();
        if (error.name === 'AbortError') {
            ToastManager.show(`⏱ Timeout starting ${image} - check container logs`, 'warning');
            setTimeout(() => location.reload(), Config.TOAST.DELAY_BEFORE_RELOAD);
        } else {
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
        }
        Utils.updateButtonState(btn, {
            disabled: false,
            originalHTML
        });
    },

    /**
     * Stop a container
     */
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
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
            this.resetStopButton(imageName);
        }
    },

    /**
     * Perform stop container
     */
    async performStopContainer(imageName, containerName) {
        const card = DOM.query(`[data-name="${imageName}"]`);
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
            const { controller, timeoutId } = Utils.createAbortController(Config.POLLING.TIMEOUT.STOP);
            const response = await ApiService.stopContainer(containerName);
            Utils.clearAbortTimeout(timeoutId);

            await this.handleStopResponse(response, imageName, containerName, btn);

        } catch (error) {
            this.handleStopError(error, containerName, btn, originalHTML);
        } finally {
            hideLoader();
        }
    },

    /**
     * Handle stop response
     */
    async handleStopResponse(response, imageName, containerName, btn) {
        if (response.ok) {
            ToastManager.show(`✓ Container ${containerName} stopped`, 'success');
            this.updateCardUI(imageName, false, '');
            ReloadManager.showReloadToast(Config.TOAST.DELAY_BEFORE_RELOAD);
        } else {
            const data = await response.json();
            const errorMsg = data.detail || 'Failed to stop container';
            ToastManager.show(`✗ Error: ${errorMsg}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML: btn.innerHTML
            });
        }
    },

    /**
     * Handle stop error
     */
    handleStopError(error, containerName, btn, originalHTML) {
        if (error.name === 'AbortError') {
            ToastManager.show(`⏱ Timeout stopping ${containerName} - container may still be stopping`, 'warning');
            Utils.updateButtonState(btn, {
                text: 'Stopping...',
                showSpinner: true
            });

            setTimeout(() => {
                ToastManager.show('📄 Reloading to check status...', 'info');
                location.reload();
            }, 3000);
        } else {
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML
            });
        }
    },

    /**
     * Reset stop button
     */
    resetStopButton(imageName) {
        const card = DOM.query(`[data-name="${imageName}"]`);
        const btn = card?.querySelector('.btn-danger');
        if (btn) {
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML: '<span class="btn-icon">⏹</span> Stop'
            });
        }
    },

    /**
     * Update card UI after status change
     */
    updateCardUI(imageName, isRunning, containerName) {
        const card = DOM.query(`[data-name="${imageName}"]`);
        if (!card) return;

        const statusIndicator = card.querySelector('.status-indicator');
        const statusText = card.querySelector('.status-text');
        const actions = card.querySelector('.card-actions');

        if (isRunning) {
            card.setAttribute('data-container', containerName);
            DOM.addClass(statusIndicator, 'status-running');
            DOM.removeClass(statusIndicator, 'status-stopped');
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
            DOM.removeClass(statusIndicator, 'status-running');
            DOM.addClass(statusIndicator, 'status-stopped');
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

window.ContainerManager = ContainerManager;