// =========================================================
// PAGE INITIALIZATION - Add Container (add-container.html)
// =========================================================

const AddContainerInit = {
    /**
     * Initialize add container page
     */
    init() {
        AddContainerManager.init();
        this.setupEventListeners();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        DOM.on(document, 'keydown', (e) => {
            if (e.key === 'Escape') {
                const confirmModal = DOM.get('confirmModal');
                if (confirmModal && DOM.hasClass(confirmModal, 'modal-open')) {
                    ModalManager.close('confirmModal');
                }
            }
        });
    }
};

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        AddContainerInit.init();
    });
} else {
    AddContainerInit.init();
}

window.AddContainerInit = AddContainerInit;