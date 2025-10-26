// =========================================================
// CONTAINER NAME BADGE MANAGER - Click to filter
// =========================================================

const ContainerNameBadgeManager = {
    /**
     * Initialize container name badge handlers
     */
    init() {
        this.initializeContainerNameBadgeHandlers();
    },

    /**
     * Initialize container name badge click handlers
     */
    initializeContainerNameBadgeHandlers() {
        const nameBadges = DOM.queryAll('.container-name-badge');
        nameBadges.forEach(badge => {
            const containerName = badge.textContent.trim();
            if (containerName) {
                DOM.on(badge, 'click', (e) => {
                    e.stopPropagation();
                    FilterManager.quickSearchContainer(containerName);
                });
                badge.style.cursor = 'pointer';
                badge.title = `Click to filter by ${containerName}`;
            }
        });
    }
};

window.ContainerNameBadgeManager = ContainerNameBadgeManager;