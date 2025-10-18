// =========================================================
// PAGE INITIALIZATION - Manager (manage.html)
// =========================================================

const ManagerInit = {
    /**
     * Initialize manager page
     */
    init() {
        this.setupEventListeners();
        SystemInfoManager.initialize();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        DOM.on(document, 'keydown', (e) => {
            if (e.key === 'Escape') {
                const logModal = DOM.get('logModal');
                const backupsModal = DOM.get('backupsModal');

                if (logModal && DOM.hasClass(logModal, 'modal-open')) {
                    ModalManager.close('logModal');
                } else if (backupsModal && DOM.hasClass(backupsModal, 'modal-open')) {
                    ModalManager.close('backupsModal');
                }
            }
        });
    }
};

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        ManagerInit.init();
    });
} else {
    ManagerInit.init();
}

window.ManagerInit = ManagerInit;
window.startCategory = CategoryOperations.startCategory.bind(CategoryOperations);
window.viewCategory = (category) => {
    window.location.href = `/?category=${category}`;
};
window.viewGroup = (groupName) => {
    window.location.href = `/?group=${encodeURIComponent(groupName)}`;
};