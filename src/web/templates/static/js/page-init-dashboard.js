// =========================================================
// PAGE INITIALIZATION - Dashboard (index.html)
// =========================================================

const DashboardInit = {
    /**
     * Initialize dashboard
     */
    init() {
        this.setupEventListeners();
        this.restorePersistentState();
        ContainerTagManager.init();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        DOM.on(document, 'keydown', (e) => {
            if (e.key === 'Escape') {
                const consoleModal = DOM.get('consoleModal');
                const logModal = DOM.get('logModal');

                if (consoleModal && DOM.hasClass(consoleModal, 'modal-open')) {
                    ConsoleManager.close();
                } else if (logModal && DOM.hasClass(logModal, 'modal-open')) {
                    LogsManager.close();
                }
            }

            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                const filterInput = DOM.get('filter');
                if (filterInput) filterInput.focus();
            }
        });
    },

    /**
     * Restore persistent state
     */
    restorePersistentState() {
        if (document.readyState === 'loading') {
            DOM.on(document, 'DOMContentLoaded', () => {
                this.restoreState();
            });
        } else {
            this.restoreState();
        }
    },

    /**
     * Restore filter and group states
     */
    restoreState() {
        ContainerTagManager.init();
        FilterPersistenceManager.restoreFilterState();
        GroupPersistenceManager.restoreGroupStates();
    }
};

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        FilterManager.init();
        DashboardInit.init();
    });
} else {
    FilterManager.init();
    DashboardInit.init();
}

window.DashboardInit = DashboardInit;