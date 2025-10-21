// =========================================================
// BULK OPERATIONS - Stop all, restart all, cleanup all
// =========================================================

const BulkOperations = {
    /**
     * Stop all running containers
     */
    async stopAllRunning() {
        try {
            const confirmed = await showConfirmModal(
                'Stop All Containers',
                'Are you sure you want to stop ALL running containers? This will gracefully stop all running playground containers.',
                'danger'
            );
            if (!confirmed) return;

            const response = await ApiService.stopAll();

            if (response.operation_id) {
                ToastManager.show(`Stop operation started. ID: ${response.operation_id}`, 'info');
                OperationMonitor.startMonitoring(response.operation_id, 'Stopping All');
                this.pollStopAllStatus(response.operation_id);
            } else {
                throw new Error(`Failed to start stop operation: ${response.error || 'Unknown error'}`);
            }
        } catch (error) {
            hideLoader(); // Safety net
            ToastManager.show(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Poll stop all status
     */
    async pollStopAllStatus(operationId) {
        let attempts = 0;

        const poll = async () => {
            try {
                const statusData = await ApiService.getOperationStatus(operationId);

                const total = statusData.total || '?';
                const stopped = statusData.stopped || 0;
                
                let loaderMessage = `Stopping containers: ${stopped} of ${total}`;
                
                // Add script tracking info if available
                const scriptStatus = Utils.formatScriptStatus(statusData);
                if (scriptStatus) {
                    loaderMessage += `\n${scriptStatus}`;
                }
                
                //showLoader(loaderMessage);

                if (statusData.status === 'completed') {
                    hideLoader(); // Safety: chiudi loader esplicitamente
                    ToastManager.show(`Stopped ${stopped} containers successfully!`, 'success');
                    setTimeout(() => {
                        location.reload();
                    }, Config.TOAST.DELAY_BEFORE_RELOAD);
                    return;
                }

                if (statusData.status === 'error') {
                    hideLoader(); // Safety: chiudi loader esplicitamente
                    ToastManager.show(`Stop operation failed: ${statusData.error}`, 'error');
                    return;
                }

                attempts++;
                if (attempts < Config.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Config.POLLING.INTERVAL);
                } else {
                    hideLoader(); // Safety: chiudi loader esplicitamente
                    ToastManager.show(`Operation timed out. Please check manually.`, 'warning');
                }

            } catch (error) {
                console.error('Polling error:', error);
                attempts++;
                if (attempts < Config.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Config.POLLING.INTERVAL);
                } else {
                    hideLoader(); // Safety: chiudi loader esplicitamente
                    ToastManager.show('An error occurred during status check.', 'error');
                }
            }
        };

        poll();
    }
};

window.BulkOperations = BulkOperations;