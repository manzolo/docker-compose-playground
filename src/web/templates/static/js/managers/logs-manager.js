// =========================================================
// LOGS MANAGER - Display and follow container logs
// =========================================================

const LogsManager = {
    currentContainer: null,
    currentImage: null,
    refreshInterval: null,
    isFollowing: false,
    refreshRate: 2000,

    /**
     * Show container logs
     */
    async show(container, image = null, follow = false) {
        try {
            this.currentContainer = container;
            this.currentImage = image;
            
            //console.log('LogsManager.show() called:', { container, image, follow });
            
            const logContainerName = DOM.get('logContainerName');
            if (logContainerName) {
                logContainerName.textContent = container;
            }
            
            const logImageName = DOM.get('logImageName');
            if (logImageName && image) {
                logImageName.textContent = image;
            }

            const data = await ApiService.getContainerLogs(container);
            //console.log('Logs fetched:', data);

            const logsContent = DOM.get('logsContent');
            if (logsContent) {
                logsContent.textContent = data.logs || 'No logs available';
            }

            this.addFollowControls();
            ModalManager.open('logModal');

            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    const logsContentElem = DOM.get('logsContent');
                    if (logsContentElem) {
                        logsContentElem.scrollTop = logsContentElem.scrollHeight;
                    }
                });
            });

            if (follow) {
                //console.log('Starting follow mode...');
                this.startFollowing();
            }
        } catch (error) {
            ToastManager.show(`Error loading logs: ${error.message}`, 'error');
            console.error('LogsManager.show() error:', error);
        }
    },

    /**
     * Add follow controls
     */
    addFollowControls() {
        const followToggleBtn = DOM.get('followToggleBtn');

        if (followToggleBtn) {
            DOM.on(followToggleBtn, 'click', () => {
                this.toggleFollow();
            });
        }

        this.updateFollowButton();
    },

    /**
     * Refresh logs
     */
    async refreshLogs() {
        if (!this.currentContainer) return;

        try {
            const data = await ApiService.getContainerLogs(this.currentContainer);
            const logsContent = DOM.get('logsContent');
            
            if (logsContent) {
                logsContent.textContent = data.logs || 'No logs available';

                // Always scroll to bottom when refreshing
                requestAnimationFrame(() => {
                    logsContent.scrollTop = logsContent.scrollHeight;
                });
            }

            this.updateFollowStatus('Last update: ' + new Date().toLocaleTimeString());
        } catch (error) {
            ToastManager.show(`Error refreshing logs: ${error.message}`, 'error');
            this.stopFollowing();
        }
    },

    /**
     * Toggle follow mode
     */
    toggleFollow() {
        if (this.isFollowing) {
            this.stopFollowing();
        } else {
            this.startFollowing();
        }
    },

    /**
     * Start following logs
     */
    startFollowing() {
        //console.log('startFollowing() called');
        this.isFollowing = true;
        this.refreshInterval = setInterval(() => {
            //console.log('Refreshing logs...');
            this.refreshLogs();
        }, this.refreshRate);

        this.updateFollowButton();
        this.updateFollowStatus('Following logs...');

        const logsContent = DOM.get('logsContent');
        if (logsContent) {
            logsContent.scrollTop = logsContent.scrollHeight;
        }
    },

    /**
     * Stop following logs
     */
    stopFollowing() {
        this.isFollowing = false;
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }

        this.updateFollowButton();
        this.updateFollowStatus('Paused');
    },

    /**
     * Update follow button state
     */
    updateFollowButton() {
        const btn = DOM.get('followToggleBtn');
        const icon = btn?.querySelector('.follow-icon');
        if (btn) {
            if (this.isFollowing) {
                DOM.addClass(btn, 'active');
                if (icon) icon.textContent = '⏸';
            } else {
                DOM.removeClass(btn, 'active');
                if (icon) icon.textContent = '▶';
            }
        }
    },

    /**
     * Update follow status message
     */
    updateFollowStatus(message) {
        const status = DOM.get('followStatus');
        if (status) {
            status.textContent = message;
        }
    },

    /**
     * Clear logs
     */
    clearLogs() {
        const logsContent = DOM.get('logsContent');
        if (logsContent) {
            logsContent.textContent = '';
        }
    },

    /**
     * Copy logs to clipboard
     */
    copyLogs() {
        const logsContent = DOM.get('logsContent');
        if (logsContent && logsContent.textContent) {
            navigator.clipboard.writeText(logsContent.textContent).then(() => {
                ToastManager.show('Logs copied to clipboard', 'success');
            }).catch(() => {
                ToastManager.show('Failed to copy logs', 'error');
            });
        }
    },

    /**
     * Toggle auto-scroll - also start/stop following logs
     */
    toggleAutoScroll() {
        const autoScrollCheckbox = DOM.get('autoScroll');
        if (autoScrollCheckbox && autoScrollCheckbox.checked) {
            // Auto-scroll is ON - start following logs
            this.startFollowing();
        } else {
            // Auto-scroll is OFF - stop following logs
            this.stopFollowing();
        }
    },

    /**
     * Close logs modal
     */
    close() {
        this.stopFollowing();
        this.currentContainer = null;
        this.currentImage = null;
        ModalManager.close('logModal');
    },

    /**
     * Set refresh rate
     */
    setRefreshRate(rate) {
        this.refreshRate = rate;
        if (this.isFollowing) {
            this.stopFollowing();
            this.startFollowing();
        }
    }
};

window.LogsManager = LogsManager;
window.showLogs = LogsManager.show.bind(LogsManager);