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

        // Save filter state whenever it changes
        const filterInput = DOM.get('filter');
        const categoryFilter = DOM.get('category-filter');

        if (filterInput) {
            DOM.on(filterInput, 'input', () => {
                FilterPersistenceManager.saveFilterState();
            });
        }

        if (categoryFilter) {
            DOM.on(categoryFilter, 'change', () => {
                FilterPersistenceManager.saveFilterState();
            });
        }

        // Save filter state when status filter buttons are clicked
        DOM.queryAll('.filter-btn').forEach(btn => {
            DOM.on(btn, 'click', () => {
                // Delay to ensure FilterManager.activeStatusFilter is updated
                setTimeout(() => {
                    FilterPersistenceManager.saveFilterState();
                }, 100);
            });
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
     * Restore filter and group states with proper timing
     */
    restoreState() {
        // Garantisci che FilterManager sia inizializzato
        FilterManager.init();
        
        // Aspetta un tick per garantire che il DOM sia totalmente pronto
        setTimeout(() => {
            ContainerTagManager.init();
            FilterPersistenceManager.restoreFilterState();
            GroupPersistenceManager.restoreGroupStates();
        }, 50);
    }
};

// Initialize on page load with proper sequencing
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