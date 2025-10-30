// =========================================================
// SCRIPT INDICATOR MANAGER - Shows script execution status in cards
// =========================================================

const ScriptIndicatorManager = {
    activeIndicators: new Map(),

    /**
     * Update script indicators based on operation status
     * Called by OperationMonitor during polling
     */
    updateIndicators(statusData) {
        const scriptsRunning = statusData.scripts_running || [];
        const scriptsCompleted = statusData.scripts_completed || [];

        // Show indicators for running scripts
        scriptsRunning.forEach(script => {
            this.showIndicator(script.container, script.type);
        });

        // Hide indicators for completed scripts
        scriptsCompleted.forEach(script => {
            // Only hide if not in running list anymore
            const stillRunning = scriptsRunning.some(s =>
                s.container === script.container && s.type === script.type
            );
            if (!stillRunning) {
                this.hideIndicator(script.container);
            }
        });
    },

    /**
     * Show script indicator in container card
     */
    showIndicator(containerName, scriptType) {
        // Extract image name from container name (remove playground- prefix)
        const imageName = containerName.replace('playground-', '');
        const card = DOM.query(`[data-name="${imageName}"]`);
        if (!card) return;

        const indicator = card.querySelector('.script-running-indicator');
        if (!indicator) return;

        // Update indicator text based on script type
        const textEl = indicator.querySelector('.script-text');
        if (textEl) {
            if (scriptType === 'post_start') {
                textEl.textContent = 'Running post-start script...';
            } else if (scriptType === 'pre_stop') {
                textEl.textContent = 'Running pre-stop script...';
            } else {
                textEl.textContent = 'Running script...';
            }
        }

        // Show indicator
        indicator.style.display = 'flex';

        // Track active indicator
        this.activeIndicators.set(containerName, {
            imageName,
            scriptType,
            startedAt: new Date()
        });
    },

    /**
     * Hide script indicator in container card
     */
    hideIndicator(containerName) {
        const imageName = containerName.replace('playground-', '');
        const card = DOM.query(`[data-name="${imageName}"]`);
        if (!card) return;

        const indicator = card.querySelector('.script-running-indicator');
        if (!indicator) return;

        // Hide indicator with fade out animation
        indicator.style.opacity = '0';
        setTimeout(() => {
            indicator.style.display = 'none';
            indicator.style.opacity = '1';
        }, 300);

        // Remove from tracking
        this.activeIndicators.delete(containerName);
    },

    /**
     * Hide all active indicators
     */
    hideAllIndicators() {
        this.activeIndicators.forEach((info, containerName) => {
            this.hideIndicator(containerName);
        });
        this.activeIndicators.clear();
    },

    /**
     * Check if a container has an active indicator
     */
    hasActiveIndicator(containerName) {
        return this.activeIndicators.has(containerName);
    },

    /**
     * Get active indicator info for a container
     */
    getIndicatorInfo(containerName) {
        return this.activeIndicators.get(containerName);
    },

    /**
     * Cleanup on page unload
     */
    cleanup() {
        this.hideAllIndicators();
    }
};

window.ScriptIndicatorManager = ScriptIndicatorManager;

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    ScriptIndicatorManager.cleanup();
});
