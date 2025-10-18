// =========================================================
// CONTAINER TAG MANAGER - Manage container tags in groups
// =========================================================

const ContainerTagManager = {
    /**
     * Initialize container tag handlers
     */
    init() {
        this.initializeContainerTagHandlers();
        this.refreshContainerTagStatuses();
    },

    /**
     * Initialize container tag click handlers
     */
    initializeContainerTagHandlers() {
        const containerTags = DOM.queryAll('.container-tag');

        containerTags.forEach(tag => {
            const containerName = tag.getAttribute('data-container');

            if (containerName) {
                DOM.on(tag, 'click', (e) => {
                    e.stopPropagation();
                    FilterManager.quickSearchContainer(containerName);
                });

                tag.style.cursor = 'pointer';
                tag.title = `Click to filter by ${containerName}`;
                this.updateContainerTagStatus(tag, containerName);
            }
        });
    },

    /**
     * Update container tag status indicator
     */
    updateContainerTagStatus(tag, containerName) {
        const statusDot = tag.querySelector('.container-status-dot');
        const matchingCard = DOM.query(`.image-card[data-name="${containerName}"]`);

        if (statusDot && matchingCard) {
            const statusText = matchingCard.querySelector('.status-text');
            if (statusText) {
                const isRunning = statusText.textContent.toLowerCase() === 'running';

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
        }
    },

    /**
     * Refresh all container tag statuses
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