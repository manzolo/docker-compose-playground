// =========================================================
// LOGS MANAGER - Display and follow container logs
// =========================================================

const LogsManager = {
    currentContainer: null,
    currentImage: null,
    refreshInterval: null,
    isFollowing: false,
    refreshRate: 2000,
    escapeListener: null, // Track escape listener per cleanup
    autoScrollListener: null, // Track auto-scroll listener

    /**
     * Show container logs
     */
    async show(container, image = null, follow = false) {
        try {
            // Cleanup precedente se esiste
            this.stopFollowing();
            
            this.currentContainer = container;
            this.currentImage = image;
            
            const logContainerName = DOM.get('logContainerName');
            if (logContainerName) {
                logContainerName.textContent = container;
            }
            
            const logImageName = DOM.get('logImageName');
            if (logImageName && image) {
                logImageName.textContent = image;
            }

            const data = await ApiService.getContainerLogs(container);

            const logsContent = DOM.get('logsContent');
            if (logsContent) {
                logsContent.textContent = data.logs || 'No logs available';
            }

            this.addFollowControls();
            ModalManager.open('logModal');

            // Scroll to bottom
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    const logsContentElem = DOM.get('logsContent');
                    if (logsContentElem) {
                        logsContentElem.scrollTop = logsContentElem.scrollHeight;
                    }
                });
            });

            // Setup Escape key listener
            this.setupEscapeListener();

            const autoScrollCheckbox = DOM.get('autoScroll');
            if (follow) {
                if (autoScrollCheckbox) {
                    autoScrollCheckbox.checked = true;
                }
            }

            if (autoScrollCheckbox && autoScrollCheckbox.checked) {
                this.startFollowing();
            }
        } catch (error) {
            ToastManager.show(`Error loading logs: ${error.message}`, 'error');
            console.error('LogsManager.show() error:', error);
        }
    },

    /**
     * Setup Escape key listener - tracciato per cleanup
     */
    setupEscapeListener() {
        // Rimuovi listener precedente se esiste
        if (this.escapeListener) {
            document.removeEventListener('keydown', this.escapeListener);
        }

        this.escapeListener = (e) => {
            if (e.key === 'Escape') {
                e.preventDefault();
                this.close();
            }
        };

        document.addEventListener('keydown', this.escapeListener);
    },

    /**
     * Add follow controls
     */
    addFollowControls() {
        const followToggleBtn = DOM.get('followToggleBtn');
        const autoScrollCheckbox = DOM.get('autoScroll');

        // Rimuovi listener vecchi se esistono
        if (this.autoScrollListener) {
            if (autoScrollCheckbox) {
                DOM.off(autoScrollCheckbox, 'change', this.autoScrollListener);
            }
        }

        if (followToggleBtn) {
            // Rimuovi listener vecchio clonando elemento
            const newBtn = followToggleBtn.cloneNode(true);
            followToggleBtn.parentNode.replaceChild(newBtn, followToggleBtn);
            
            const updatedBtn = DOM.get('followToggleBtn');
            if (updatedBtn) {
                DOM.on(updatedBtn, 'click', () => {
                    this.toggleFollow();
                });
            }
        }

        // Aggiungi auto-scroll listener
        if (autoScrollCheckbox) {
            this.autoScrollListener = () => {
                this.toggleAutoScroll();
            };
            DOM.on(autoScrollCheckbox, 'change', this.autoScrollListener);
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
            console.error('Error refreshing logs:', error);
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
     * Start following logs - con interval tracciato
     */
    startFollowing() {
        if (this.isFollowing) return;
        
        this.isFollowing = true;
        
        // Rimuovi interval precedente se esiste
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        this.refreshInterval = setInterval(() => {
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
     * Stop following logs - con cleanup di interval
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
        if (!btn) return;

        const icon = btn.querySelector('.follow-icon');
        if (this.isFollowing) {
            DOM.addClass(btn, 'active');
            if (icon) icon.textContent = '⏸';
        } else {
            DOM.removeClass(btn, 'active');
            if (icon) icon.textContent = '▶';
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
            this.startFollowing();
        } else {
            this.stopFollowing();
        }
    },

    /**
     * Close logs modal - with proper cleanup
     */
    close() {
        // Ferma il following
        this.stopFollowing();

        // Rimuovi escape listener
        if (this.escapeListener) {
            document.removeEventListener('keydown', this.escapeListener);
            this.escapeListener = null;
        }

        // Rimuovi auto-scroll listener
        if (this.autoScrollListener) {
            const autoScrollCheckbox = DOM.get('autoScroll');
            if (autoScrollCheckbox) {
                DOM.off(autoScrollCheckbox, 'change', this.autoScrollListener);
            }
            this.autoScrollListener = null;
        }

        // Reset stato
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
    },

    /**
     * Cleanup su beforeunload
     */
    cleanup() {
        this.close();
    }
};

window.LogsManager = LogsManager;
window.showLogs = LogsManager.show.bind(LogsManager);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    LogsManager.cleanup();
});