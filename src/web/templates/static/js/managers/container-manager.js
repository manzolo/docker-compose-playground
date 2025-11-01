// =========================================================
// CONTAINER MANAGER - updated for new container cards
// =========================================================

const ContainerManager = {
    /**
     * Refresh a single container card state without page reload
     * @param {string} containerName - Container name (with or without playground- prefix)
     */
    async refreshCardState(containerName) {
        try {
            // Ensure container name has the playground- prefix for API call
            const fullContainerName = ContainerNameUtils.toFullName(containerName);

            // Extract display name (without playground- prefix) for finding the card
            const displayName = ContainerNameUtils.toDisplayName(containerName);
            const card = DOM.query(`[data-name="${displayName}"]`);
            if (!card) return;

            // Get container info from API (always returns 200, even if container doesn't exist)
            const response = await ApiService.getContainerInfo(fullContainerName);

            // Check if container exists and is running
            // status can be: "running", "exited", "paused", "not_found", etc.
            const isRunning = response.exists && response.status === 'running';

            if (!response.exists) {
                // console.log(`Container ${fullContainerName} not found (stopped/removed), updating UI to stopped state`);
            }

            // Use updateCardUI to rebuild the buttons with correct state
            // This ensures all buttons are created/removed appropriately
            this.updateCardUI(displayName, isRunning, fullContainerName);

            // Update filter counts
            if (window.FilterManager) {
                FilterManager.updateCounts();
            }

        } catch (error) {
            console.error('Error refreshing card state:', error);
        }
    },

    /**
     * start a container
     */
    async startContainer(image) {
        const card = DOM.query(`[data-name="${image}"]`);
        const btn = card?.querySelector('.btn-start');
        if (!btn) return;

        const originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span>';

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
     * restart a container
     */
    async restartContainer(image) {
        try {
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
            btn.disabled = true;
            btn.innerHTML = '<span>⏳</span>';

            const response = await ApiService.restartContainer(image);

            if (response.operation_id) {
                OperationMonitor.startMonitoring(response.operation_id, `Restarting ${image}`);
                await this.pollRestartStatus(response.operation_id, image, btn, originalHTML);
            } else {
                throw new Error('No operation_id received');
            }

        } catch (error) {
            hideLoader();
            this.handleRestartError(error, image, btn, originalHTML);
        }
    },

    /**
     * poll restart status
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
                    this.updateCardUI(image, true, statusData.container || `playground-${image}`);
                }

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
            hideLoader();
            ToastManager.show(`✗ Error polling container status: ${error.message}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML
            });
        }
    },

    /**
     * format restart status message
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
     * handle restart error
     */
    handleRestartError(error, image, btn, originalHTML) {
        if (error.name === 'AbortError') {
            ToastManager.show(`⏱ Timeout restarting ${image} - check container logs`, 'warning');
        } else {
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
        }
        Utils.updateButtonState(btn, {
            disabled: false,
            originalHTML
        });
    },

    /**
     * cleanup a container
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
            hideLoader();
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
        }
    },

    /**
     * perform cleanup
     */
    async performCleanup(containerName) {
        try {
            const response = await ApiService.cleanupContainer(containerName);

            if (response.operation_id) {
                OperationMonitor.startMonitoring(response.operation_id, `Cleaning up ${containerName}`);
            } else {
                throw new Error('No operation_id received');
            }
        } catch (error) {
            // console.error("Error in performCleanup:", error);
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
        }
    },

    /**
     * poll container status
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
                    this.updateCardUI(image, true, statusData.container || `playground-${image}`);
                }

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
            hideLoader();
            ToastManager.show(`✗ Error polling container status: ${error.message}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML
            });
        }
    },

    /**
     * format container status message
     */
    formatContainerStatusMessage(statusData, image) {
        const total = statusData.total || 1;
        const started = statusData.started || 0;
        const failed = statusData.failed || 0;
        const completed = started + failed;
        const remaining = total - completed;

        let message = '';

        if (statusData.status === 'running') {
            message = `Starting '${image}': ${completed}/${total}\n` +
                `✓ ${started} started | ✗ ${failed} failed | ⏳ ${remaining} remaining`;

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
     * handle start error
     */
    handleStartError(error, image, btn, originalHTML) {
        if (error.name === 'AbortError') {
            ToastManager.show(`⏱ Timeout starting ${image} - check container logs`, 'warning');
        } else {
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
        }
        Utils.updateButtonState(btn, {
            disabled: false,
            originalHTML
        });
    },

    /**
     * stop a container
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
     * perform stop container
     */
    async performStopContainer(imageName, containerName) {
        const card = DOM.query(`[data-name="${imageName}"]`);
        const btn = card?.querySelector('.btn-stop');
        if (!btn) return;

        const originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span>';

        try {
            const response = await ApiService.stopContainer(containerName);

            if (response.operation_id) {
                OperationMonitor.startMonitoring(response.operation_id, `Stopping ${containerName}`);
            } else {
                throw new Error('No operation_id received from server');
            }

        } catch (error) {
            hideLoader();
            this.handleStopError(error, containerName, btn, originalHTML);
        }
    },

    /**
     * handle stop error
     */
    handleStopError(error, containerName, btn, originalHTML) {
        if (error.name === 'AbortError') {
            ToastManager.show(`⏱ Timeout stopping ${containerName} - container may still be stopping`, 'warning');
            Utils.updateButtonState(btn, {
                text: 'Stopping...',
                showSpinner: true
            });
        } else {
            ToastManager.show(`✗ Error: ${error.message}`, 'error');
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML
            });
        }
    },

    /**
     * reset stop button
     */
    resetStopButton(imageName) {
        const card = DOM.query(`[data-name="${imageName}"]`);
        const btn = card?.querySelector('.btn-stop');
        if (btn) {
            Utils.updateButtonState(btn, {
                disabled: false,
                originalHTML: '<span>⏹</span><span>Stop</span>'
            });
        }
    },

    /**
     * update card ui after status change - new html structure with all buttons
     */
    updateCardUI(imageName, isRunning, containerName) {
        const card = DOM.query(`[data-name="${imageName}"]`);
        if (!card) return;

        const nameBadge = card.querySelector('.container-name-badge');
        const statusDot = card.querySelector('.container-name-badge .status-dot');
        const actionsContainer = card.querySelector('.container-actions');

        if (!actionsContainer) {
            console.error('container-actions not found for', imageName);
            return;
        }

        const commandsData = card.getAttribute('data-commands') || '';

        if (isRunning) {
            card.setAttribute('data-container', containerName);

            if (nameBadge) {
                nameBadge.classList.remove('stopped');
                nameBadge.classList.add('running');
            }

            if (statusDot) {
                statusDot.classList.remove('stopped');
                statusDot.classList.add('running');
            }

            actionsContainer.innerHTML = `
                <button class="btn-primary-action btn-stop"
                    onclick="ContainerManager.stopContainer('${imageName}', '${containerName}')">
                    <span>⏹</span>
                    <span>Stop</span>
                </button>

                <div class="container-quick-actions">
                    <button class="btn-quick-action quick-commands"
                        data-commands='${commandsData}'
                        data-container="${containerName}"
                        data-image="${imageName}"
                        onclick="QuickCommandsManager.openFromElement(this)"
                        title="View quick commands">📋</button>

                    <button class="btn-quick-action restart"
                        data-action="restart"
                        onclick="ContainerManager.restartContainer('${imageName}')"
                        title="Restart container">🔄</button>

                    <button class="btn-quick-action logs"
                        onclick="LogsManager.show('${containerName}', '${imageName}', true)"
                        title="View logs">📄</button>

                    <button class="btn-quick-action console"
                        onclick="ConsoleManager.open('${containerName}', '${imageName}')"
                        title="Open console">💻</button>

                    <button class="btn-quick-action execute"
                        onclick="ExecuteCommandManager.open('${containerName}', '${imageName}')"
                        title="Execute shell command">⚡</button>

                    <button class="btn-quick-action diagnostics"
                        onclick="ExecuteCommandManager.openDiagnostics('${containerName}', '${imageName}')"
                        title="Run diagnostics">🔍</button>

                    <button class="btn-quick-action clean"
                        onclick="ContainerManager.cleanupContainer('${containerName}')"
                        title="Clean container data">🧹</button>
                </div>
            `;
        } else {
            card.removeAttribute('data-container');

            if (nameBadge) {
                nameBadge.classList.remove('running');
                nameBadge.classList.add('stopped');
            }

            if (statusDot) {
                statusDot.classList.remove('running');
                statusDot.classList.add('stopped');
            }

            actionsContainer.innerHTML = `
                <button class="btn-primary-action btn-start"
                    onclick="ContainerManager.startContainer('${imageName}')">
                    <span>▶</span>
                    <span>Start</span>
                </button>

                <div class="container-quick-actions">
                    <button class="btn-quick-action clean" 
                        onclick="ContainerManager.cleanupContainer('${imageName}')"
                        title="Clean container data">🧹</button>
                </div>
            `;
        }

        if (ContainerTagManager && ContainerTagManager.reinitializeHandlers) {
            ContainerTagManager.reinitializeHandlers();
        }
    }

};

window.ContainerManager = ContainerManager;