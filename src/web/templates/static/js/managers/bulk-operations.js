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

            showLoader('Initiating stop all operation...');
            ToastManager.show('Initiating stop all operation...', 'info');

            const data = await ApiService.stopAll();

            if (data.operation_id) {
                ToastManager.show(`Stop operation started. ID: ${data.operation_id}`, 'info');
                this.pollStopAllStatus(data.operation_id);
            } else {
                ToastManager.show(`Failed to start stop operation: ${data.error || 'Unknown error'}`, 'error');
                hideLoader();
            }
        } catch (error) {
            ToastManager.show(`Error: ${error.message}`, 'error');
            hideLoader();
        }
    },

    /**
     * Poll stop all status
     */
    async pollStopAllStatus(operationId) {
        let attempts = 0;

        showLoader('Stopping containers: Awaiting progress...');

        const poll = async () => {
            try {
                const statusData = await ApiService.getOperationStatus(operationId);

                const total = statusData.total || '?';
                const stopped = statusData.stopped || 0;
                showLoader(`Stopping containers: ${stopped} of ${total} | Status: ${statusData.status}`);

                if (statusData.status === 'completed') {
                    ToastManager.show(`Stopped ${stopped} containers successfully!`, 'success');
                    hideLoader();

                    setTimeout(() => {
                        location.reload();
                    }, Config.TOAST.DELAY_BEFORE_RELOAD);
                    return;
                }

                if (statusData.status === 'error') {
                    ToastManager.show(`Stop operation failed: ${statusData.error}`, 'error');
                    hideLoader();
                    return;
                }

                attempts++;
                if (attempts < Config.POLLING.MAX_ATTEMPTS) {
                    setTimeout(poll, Config.POLLING.INTERVAL);
                } else {
                    ToastManager.show(`Operation timed out. Please check manually.`, 'warning');
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

window.BulkOperations = BulkOperations;