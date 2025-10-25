// =========================================================
// CONTAINER MANAGER - Start, stop, and manage containers
// =========================================================

const ContainerManager = {
    /**
     * Start a container
     */
    async startContainer(image) {
        const card = DOM.query(`[data-name="${image}"]`);
        const btn = card?.querySelector('.btn-start-minimal');
        if (!btn) return;

        const originalHTML = btn.innerHTML;

        // Mostra solo lo spinner
        btn.disabled = true;
        btn.innerHTML = '<span class="btn-icon-large spinner">⏳</span>';

        try {
            const response = await ApiService.startContainer(image);

            if (response.operation_id) {
                OperationMonitor.startMonitoring(response.operation_id, `Starting ${image}`);
                await this.pollContainerStatus(response.operation_id, image, btn, originalHTML);
            } else {
                throw new Error('No operation_id received from server');
            }

        } catch (error) {
            hideLoader();
            this.handleStartError(error, image, btn, originalHTML);
        }
    },

    /**
     * Restart a container
     */
    async restartContainer(image) {
        try {
            // Chiedi conferma prima di procedere
            const confirmed = await showConfirmModal(
                'Restart Container',
                `Are you sure you want to restart container <strong>${image}</strong>?`,
                'warning'
            );
            if (!confirmed) return;

            const card = DOM.query(`[data-name="${image}"]`);
            const btn = card?.querySelector('[data-action="restart"]');
            if (!btn) return;

            const originalHTML = btn.innerHTML;

            // Mostra solo lo spinner senza testo
            btn.disabled = true;
            btn.innerHTML = '<span class="btn-icon-large spinner">⏳</span>';

            const response = await ApiService.restartContainer(image);

            if (response.operation_id) {
                OperationMonitor.startMonitoring(response.operation_id, `Restarting ${image}`);
                await this.pollRestartStatus(response.operation_id, image, btn, originalHTML);
            } else {
                throw new Error('No operation_id received from server');
            }

        } catch (error) {
            hideLoader();
            this.handleRestartError(error, image, btn, originalHTML);
        }
    },

    /**
     * Poll restart status
     */
    async pollRestartStatus(operationId, image, btn, originalHTML) {
        try {
            const statusData = await Utils.pollOperationStatus(
                operationId,
                (data) => this.formatRestartStatusMessage(data, image),
                {
                    maxAttempts: Config.POLLING.MAX_ATTEMPTS,
                    interval: Config.POLLING.INTERVAL
                }
            );

            if (statusData.status === 'completed') {
                const restarted = statusData.restarted || 0;

                if (restarted > 0) {
                    //ToastManager.show(`✓ Container ${image} restarted successfully!`, 'success');
                }

                this.updateCardUI(image, true, statusData.container || `playground-${image}`);
                ReloadManager.showReloadToast(Config.TOAST.DELAY_BEFORE_RELOAD);

            } else if (statusData.status === 'error') {
                const errorMsg = statusData.error || 'Unknown error';
                ToastManager.show(`✗ Failed to restart ${image}: ${errorMsg}`, 'error');

                if (statusData.errors && statusData.errors.length > 0) {
                    ToastManager.showErrorsSequentially(statusData.errors, `Errors restarting ${image}:`);
                }

                Utils.updateButtonState(btn, {
                    disabled: false,
                    originalHTML
                });
            }
        } catch (error) {
            hideLoader(); // Safety net
            ToastManager.show(`✗ Error polling container status: ${error.message}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML
            });
        }
    },

    /**
     * Format restart status message
     */
    formatRestartStatusMessage(statusData, image) {
        const total = statusData.total || 1;
        const restarted = statusData.restarted || 0;
        const failed = statusData.failed || 0;
        const completed = restarted + failed;
        const remaining = total - completed;

        let message = '';

        if (statusData.status === 'running') {
            message = `Restarting '${image}': ${completed}/${total}\n` +
                `✓ ${restarted} restarted | ✗ ${failed} failed | ⏳ ${remaining} remaining`;

            // Add script tracking info if available
            const scriptStatus = Utils.formatScriptStatus(statusData);
            if (scriptStatus) {
                message += `\n${scriptStatus}`;
            }
        } else if (statusData.status === 'completed') {
            message = `Container '${image}' restarted successfully! ✓`;
        } else {
            message = `Restarting container '${image}'...`;
        }

        return message;
    },

    /**
     * Handle restart error
     */
    handleRestartError(error, image, btn, originalHTML) {
        if (error.name === 'AbortError') {
            ToastManager.show(`⏱ Timeout restarting ${image} - check container logs`, 'warning');
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
     * Cleanup a container
     */
    async cleanupContainer(containerName) {
        try {
            const confirmed = await showConfirmModal(
                'Cleanup Container',
                `Are you sure you want to cleanup container <strong>${containerName}</strong>? This will remove docker image and volume data.`,
                'warning'
            );
            if (!confirmed) return;

            await this.performCleanup(containerName);
        } catch (error) {
            hideLoader(); // Safety net
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
        }
    },

    /**
     * Perform cleanup
     */
    async performCleanup(containerName) {
        try {
            const response = await ApiService.cleanupContainer(containerName);

            // ApiService.cleanupContainer ritorna direttamente l'oggetto JSON
            if (response.operation_id) {
                OperationMonitor.startMonitoring(response.operation_id, `Cleaning up ${containerName}`);

            } else {
                throw new Error('No operation_id received');
            }
        } catch (error) {
            console.error("Error in performCleanup:", error);
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
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
                    //ToastManager.show(`✓ Container ${image} started successfully!`, 'success');
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
            hideLoader(); // Safety net
            ToastManager.show(`✗ Error polling container status: ${error.message}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML
            });
        }
    },

    /**
     * Format container status message with script tracking
     */
    formatContainerStatusMessage(statusData, image) {
        const total = statusData.total || 1;
        const started = statusData.started || 0;
        const alreadyRunning = statusData.already_running || 0;
        const failed = statusData.failed || 0;
        const completed = started + alreadyRunning + failed;
        const remaining = total - completed;

        let message = '';

        if (statusData.status === 'running') {
            message = `Starting '${image}': ${completed}/${total}\n` +
                `✓ ${started} started | ⚡ ${alreadyRunning} running | ✗ ${failed} failed | ⏳ ${remaining} remaining`;

            // Add script tracking info if available
            const scriptStatus = Utils.formatScriptStatus(statusData);
            if (scriptStatus) {
                message += `\n${scriptStatus}`;
            }
        } else if (statusData.status === 'completed') {
            message = `Container '${image}' started successfully! ✓`;
        } else {
            message = `Starting container '${image}'...`;
        }

        return message;
    },

    /**
     * Handle start error
     */
    handleStartError(error, image, btn, originalHTML) {
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
            hideLoader();
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
            this.resetStopButton(imageName);
        }
    },

    /**
     * Perform stop container
     */
    async performStopContainer(imageName, containerName) {
        const card = DOM.query(`[data-name="${imageName}"]`);
        const btn = card?.querySelector('.btn-stop-minimal');
        if (!btn) return;

        const originalHTML = btn.innerHTML;

        // Mostra solo lo spinner
        btn.disabled = true;
        btn.innerHTML = '<span class="btn-icon-large spinner">⏳</span>';

        try {
            const response = await ApiService.stopContainer(containerName);

            if (response.operation_id) {
                OperationMonitor.startMonitoring(response.operation_id, `Stopping ${containerName}`);
                //await this.pollStopStatus(response.operation_id, imageName, containerName, btn, originalHTML);
            } else {
                throw new Error('No operation_id received from server');
            }

        } catch (error) {
            hideLoader();
            this.handleStopError(error, containerName, btn, originalHTML);
        }
    },

    /**
     * Handle stop response
     */
    async handleStopResponse(response, imageName, containerName, btn) {
        if (response.ok) {
            //ToastManager.show(`✓ Container ${containerName} stopped`, 'success');
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
        const actionsContainer = card.querySelector('.card-actions-minimal');

        if (!actionsContainer) {
            console.error('card-actions-minimal not found for', imageName);
            return;
        }

        if (isRunning) {
            // CONTAINER IN ESECUZIONE
            card.setAttribute('data-container', containerName);
            DOM.addClass(statusIndicator, 'status-running');
            DOM.removeClass(statusIndicator, 'status-stopped');
            if (statusText) statusText.textContent = 'Running';

            actionsContainer.innerHTML = `
            <div class="actions-bar">
                <button class="btn-primary-action btn-stop-minimal"
                    onclick="ContainerManager.stopContainer('${imageName}', '${containerName}')">
                    <span class="btn-icon-large">⏹</span>
                    <span class="btn-label">Stop</span>
                </button>

                <button class="btn-quick-action btn-restart-minimal" 
                    data-action="restart"
                    onclick="ContainerManager.restartContainer('${imageName}')"
                    title="Restart container">
                    <span class="btn-icon-large">🔄</span>
                </button>

                <button class="btn-quick-action btn-logs-minimal" 
                    onclick="showLogs('${containerName}')"
                    title="View logs">
                    <span class="btn-icon-large">📋</span>
                </button>

                <button class="btn-quick-action btn-console-minimal" 
                    onclick="ConsoleManager.open('${containerName}', '${imageName}')"
                    title="Open console">
                    <span class="btn-icon-large">💻</span>
                </button>

                <button class="btn-quick-action btn-clean-minimal" 
                    onclick="ContainerManager.cleanupContainer('${containerName}', '${imageName}')"
                    title="Clean container data">
                    <span class="btn-icon-large">🧹</span>
                </button>
            </div>
        `;
        } else {
            // CONTAINER FERMO
            card.removeAttribute('data-container');
            DOM.removeClass(statusIndicator, 'status-running');
            DOM.addClass(statusIndicator, 'status-stopped');
            if (statusText) statusText.textContent = 'Stopped';

            actionsContainer.innerHTML = `
            <div class="actions-bar">
                <button class="btn-primary-action btn-start-minimal btn-start-large"
                    onclick="ContainerManager.startContainer('${imageName}')">
                    <span class="btn-icon-large">▶</span>
                    <span class="btn-label">Start Container</span>
                </button>

                <button class="btn-quick-action btn-clean-minimal" 
                    onclick="ContainerManager.cleanupContainer('${imageName}', '${imageName}')"
                    title="Clean container data">
                    <span class="btn-icon-large">🧹</span>
                </button>
            </div>
        `;
        }

        FilterManager.applyFilters();
    }

};

window.ContainerManager = ContainerManager;