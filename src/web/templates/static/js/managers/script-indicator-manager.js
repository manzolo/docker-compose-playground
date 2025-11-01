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

        // 1. Update single container card indicator (if exists)
        const card = DOM.query(`[data-name="${imageName}"]`);
        if (card) {
            const indicator = card.querySelector('.script-running-indicator');
            if (indicator) {
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

                // Show indicator with proper opacity reset
                indicator.style.opacity = '1';
                indicator.style.display = 'flex';
            }
        }

        // 2. Update container tags in groups (change dot to yellow)
        // Use imageName (without 'playground-' prefix) to match data-container attribute
        const containerTag = DOM.query(`.container-tag[data-container="${imageName}"]`);
        if (containerTag) {
            containerTag.setAttribute('data-script-running', 'true');
            // Update inline style to override container-tag-manager styles
            const statusDot = containerTag.querySelector('.container-status-dot');
            if (statusDot) {
                statusDot.style.background = '#f59e0b';
                statusDot.style.animation = 'pulse-dot 1.5s ease-in-out infinite';
            }
        }

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

        // 1. Hide single container card indicator (if exists)
        const card = DOM.query(`[data-name="${imageName}"]`);
        if (card) {
            const indicator = card.querySelector('.script-running-indicator');
            if (indicator) {
                // Hide indicator with fade out animation
                indicator.style.opacity = '0';
                setTimeout(() => {
                    indicator.style.display = 'none';
                    indicator.style.opacity = '1';
                }, 300);
            }
        }

        // 2. Remove yellow dot from container tags in groups
        // Use imageName (without 'playground-' prefix) to match data-container attribute
        const containerTag = DOM.query(`.container-tag[data-container="${imageName}"]`);
        if (containerTag) {
            containerTag.removeAttribute('data-script-running');
            // Restore color based on running state
            const statusDot = containerTag.querySelector('.container-status-dot');
            const isRunning = containerTag.getAttribute('data-running') === 'true';
            if (statusDot) {
                if (isRunning) {
                    // Restore green if container is running
                    statusDot.style.background = '#10b981';
                    statusDot.style.animation = 'pulse 2s ease-in-out infinite';
                } else {
                    // Restore gray if container is stopped
                    statusDot.style.background = '#94a3b8';
                    statusDot.style.animation = 'none';
                }
            }
        }

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
