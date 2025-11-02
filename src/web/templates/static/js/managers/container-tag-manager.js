// =========================================================
// CONTAINER TAG MANAGER - manage container tags in groups + name badges
// =========================================================
const ContainerTagManager = {
    initialized: false,

    /**
     * initialize container tag and name badge handlers
     */
    init() {
        if (!this.initialized) {
            this.initializeClickHandlers();
            this.initialized = true;
        }
        this.refreshContainerTagStatuses();
    },

    /**
     * reinitialize only click handlers without triggering filter
     * used after DOM changes (e.g., after updateCardUI)
     */
    reinitializeHandlers() {
        this.refreshContainerTagStatuses();
    },

    /**
     * initialize click handlers for both container tags and name badges
     * uses event delegation to avoid duplicate listeners
     */
    initializeClickHandlers() {
        // Use event delegation - single listener on document
        document.addEventListener('click', (e) => {
            // Check if click was on container-tag or container-name-badge
            const tag = e.target.closest('.container-tag');
            const badge = e.target.closest('.container-name-badge');

            if (tag) {
                e.stopPropagation();
                const containerName = tag.getAttribute('data-container');
                if (containerName) {
                    FilterManager.quickSearchContainer(containerName);
                }
            } else if (badge) {
                e.stopPropagation();
                const containerName = badge.getAttribute('data-container');
                if (containerName) {
                    FilterManager.quickSearchContainer(containerName);
                }
            }
        });

        // Set cursor and title for existing elements
        this.updateElementStyles();
    },

    /**
     * Update cursor and title for container tags and badges
     */
    updateElementStyles() {
        const containerTags = DOM.queryAll('.container-tag');
        containerTags.forEach(tag => {
            const containerName = tag.getAttribute('data-container');
            if (containerName) {
                tag.style.cursor = 'pointer';
                tag.title = `Click to filter by ${containerName}`;
            }
        });

        const nameBadges = DOM.queryAll('.container-name-badge');
        nameBadges.forEach(badge => {
            badge.style.cursor = 'pointer';
        });
    },

    /**
     * update container tag status indicator
     */
    updateContainerTagStatus(tag, containerName) {
        // Don't update if tag is currently showing operation/script status
        // ScriptIndicatorManager will manage the state during operations
        if (tag.hasAttribute('data-operation-running') || tag.hasAttribute('data-script-running')) {
            return;
        }

        // Don't update if ScriptIndicatorManager just set the final state
        // Remove the flag after reading it to allow future updates
        if (tag.hasAttribute('data-final-state-set')) {
            tag.removeAttribute('data-final-state-set');
            return;
        }

        const statusDot = tag.querySelector('.container-status-dot');
        const matchingCard = DOM.query(`.container-card[data-name="${containerName}"]`);
        if (statusDot && matchingCard) {
            const statusDot2 = matchingCard.querySelector('.status-dot');
            const isRunning = statusDot2 && statusDot2.classList.contains('running');
            if (isRunning) {
                statusDot.style.background = '#10b981';
                statusDot.style.animation = 'pulse 2s ease-in-out infinite';
                tag.setAttribute('data-running', 'true');
            } else {
                statusDot.style.background = '#94a3b8';
                statusDot.style.animation = 'none';
                tag.setAttribute('data-running', 'false');
            }
        }
    },

    /**
     * refresh all container tag statuses
     */
    refreshContainerTagStatuses() {
        const containerTags = DOM.queryAll('.container-tag');
        containerTags.forEach(tag => {
            const containerName = tag.getAttribute('data-container');
            if (containerName) {
                this.updateContainerTagStatus(tag, containerName);
            }
        });
    }
};
window.ContainerTagManager = ContainerTagManager;