// =========================================================
// CONTAINER TAG MANAGER - manage container tags in groups + name badges
// =========================================================
const ContainerTagManager = {
    /**
     * initialize container tag and name badge handlers
     */
    init() {
        this.initializeClickHandlers();
        this.refreshContainerTagStatuses();
    },

    /**
     * reinitialize only click handlers without triggering filter
     * used after DOM changes (e.g., after updateCardUI)
     */
    reinitializeHandlers() {
        this.attachClickListeners();
        this.refreshContainerTagStatuses();
    },

    /**
     * initialize click handlers for both container tags and name badges
     * consolidated to avoid duplicate filter calls
     */
    initializeClickHandlers() {
        this.attachClickListeners();
    },

    /**
     * attach click event listeners to tags and badges
     */
    attachClickListeners() {
        // container tag handlers (in groups)
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
            }
        });

        // container name badge handlers (on container cards)
        const nameBadges = DOM.queryAll('.container-name-badge');
        nameBadges.forEach(badge => {
            const containerName = badge.getAttribute('data-container');
            if (containerName) {
                DOM.on(badge, 'click', (e) => {
                    e.stopPropagation();
                    FilterManager.quickSearchContainer(containerName);
                });
                badge.style.cursor = 'pointer';
            }
        });
    },

    /**
     * update container tag status indicator
     */
    updateContainerTagStatus(tag, containerName) {
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