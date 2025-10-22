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
            // Avvia il container SENZA mostrare il loader
            const response = await ApiService.startContainer(image);

            if (response.operation_id) {
                //ToastManager.show(`Starting container ${image}...`, 'info');
                // Mostra il widget di monitoraggio
                OperationMonitor.startMonitoring(response.operation_id, `Starting ${image}`);
                await this.pollContainerStatus(response.operation_id, image, btn, originalHTML);
            } else {
                throw new Error('No operation_id received from server');
            }

        } catch (error) {
            hideLoader(); // Safety net
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
            hideLoader(); // Safety net
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

        try {
            //console.log("🔴 Calling /stop/" + containerName);
            const response = await ApiService.stopContainer(containerName);

            //console.log("🔴 Response received:", response);

            const data = response instanceof Response ? await response.json() : response;
            //console.log("🔴 Data parsed:", data);

            if (data.operation_id) {
                //console.log("🔴 operation_id:", data.operation_id);
                //ToastManager.show(`Stopping ${containerName}...`, 'info');
                OperationMonitor.startMonitoring(data.operation_id, `Stopping ${containerName}`);
                //console.log("🔴 Widget monitoring started");
            } else {
                console.error("🔴 No operation_id in response:", data);
                throw new Error('No operation_id received');
            }

        } catch (error) {
            console.error("🔴 Error in performStopContainer:", error);
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