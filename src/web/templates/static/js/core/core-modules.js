// =========================================================
// CORE MODULES - Shared across all pages
// =========================================================

// =========================================================
// Configuration
// =========================================================
const Config = {
    POLLING: {
        MAX_ATTEMPTS: 180,
        INTERVAL: 1000,
        TIMEOUT: {
            START: 180000,
            STOP: 180000,
            RESTART: 180000,
            CLEANUP: 60000,
            GROUP: 180000
        }
    },
    TOAST: {
        DISPLAY_TIME: 4000,
        DELAY_BEFORE_RELOAD: 4500
    },
    ICONS: {
        success: '✓',
        error: '✗',
        info: 'ℹ',
        warning: '⚠'
    }
};

// =========================================================
// DOM Helper with cache for repeated queries
// =========================================================
const DOM = {
    cache: {}, // Cache per riduire DOM queries

    get(id) {
        if (!this.cache[id]) {
            this.cache[id] = document.getElementById(id);
        }
        return this.cache[id];
    },

    invalidateCache(id) {
        delete this.cache[id];
        if (id) {
            this.cache[id] = document.getElementById(id);
        }
    },
    
    query(selector) {
        return document.querySelector(selector);
    },
    
    queryAll(selector) {
        return document.querySelectorAll(selector);
    },
    
    on(element, event, handler) {
        if (element) {
            element.addEventListener(event, handler);
        }
    },

    off(element, event, handler) {
        if (element) {
            element.removeEventListener(event, handler);
        }
    },
    
    addClass(element, className) {
        if (element) element.classList.add(className);
    },
    
    removeClass(element, className) {
        if (element) element.classList.remove(className);
    },
    
    toggleClass(element, className, force) {
        if (element) {
            if (force !== undefined) {
                element.classList.toggle(className, force);
            } else {
                element.classList.toggle(className);
            }
        }
    },
    
    hasClass(element, className) {
        return element && element.classList.contains(className);
    }
};

// =========================================================
// Utility Functions
// =========================================================
const Utils = {
    createAbortController(timeoutMs) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        return { controller, timeoutId };
    },

    clearAbortTimeout(timeoutId) {
        if (timeoutId) clearTimeout(timeoutId);
    },

    parseHTMLResponse(text) {
        const parser = new DOMParser();
        return parser.parseFromString(text, 'text/html');
    },

    updateButtonState(button, options = {}) {
        const {
            disabled = false,
            text = '',
            showSpinner = false,
            originalHTML = null
        } = options;

        if (disabled !== undefined) button.disabled = disabled;

        if (text) {
            button.innerHTML = showSpinner
                ? `<span class="spinner"></span> ${text}`
                : text;
        } else if (originalHTML) {
            button.innerHTML = originalHTML;
        }
    },

    async pollOperationStatus(operationId, messageFormatter, options = {}) {
        const { 
            maxAttempts = Config.POLLING.MAX_ATTEMPTS, 
            interval = Config.POLLING.INTERVAL 
        } = options;
        let attempts = 0;
        let statusData = null;

        return new Promise((resolve, reject) => {
            const poll = () => {
                fetch(`/api/operation-status/${operationId}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        statusData = data;

                        // Se completato o errore, risolvere
                        if (statusData.status === 'completed' || statusData.status === 'error') {
                            hideLoader();
                            resolve(statusData);
                            return;
                        }

                        // Altrimenti, schedule il prossimo polling
                        attempts++;
                        if (attempts < maxAttempts) {
                            setTimeout(poll, interval);
                        } else {
                            hideLoader();
                            reject(new Error(`Operation timed out after ${maxAttempts} attempts`));
                        }
                    })
                    .catch(error => {
                        console.error('Polling error:', error);
                        attempts++;
                        
                        if (attempts < maxAttempts) {
                            setTimeout(poll, interval);
                        } else {
                            hideLoader();
                            reject(error);
                        }
                    });
            };

            poll();
        });
    },

    /**
     * Format script tracking info for display
     */
    formatScriptStatus(statusData) {
        const scriptsRunning = statusData.scripts_running || [];
        const scriptsCompleted = statusData.scripts_completed || [];

        let message = '';

        if (scriptsRunning.length > 0) {
            message += '📝 Running scripts: ';
            const runningNames = scriptsRunning.map(s => {
                const elapsed = this.getElapsedTime(s.started_at);
                return `${s.type} (${elapsed})`;
            }).join(', ');
            message += runningNames;
        }

        if (scriptsCompleted.length > 0) {
            if (message) message += ' | ';
            message += '✓ Completed: ';
            const completedNames = scriptsCompleted.map(s => `${s.type}`).join(', ');
            message += completedNames;
        }

        return message;
    },

    /**
     * Calculate elapsed time from ISO timestamp
     */
    getElapsedTime(startedAt) {
        try {
            const start = new Date(startedAt);
            const now = new Date();
            const seconds = Math.floor((now - start) / 1000);
            
            if (seconds < 60) return `${seconds}s`;
            const minutes = Math.floor(seconds / 60);
            return `${minutes}m ${seconds % 60}s`;
        } catch (e) {
            return '--';
        }
    }
};

// =========================================================
// Toast Notification System
// =========================================================
const ToastManager = {
    activeToasts: [], // Track toasts para cleanup

    show(message, type = 'info') {
        const container = DOM.get('toast-container');
        if (!container) {
            console.warn('Toast container is missing. Message:', message);
            return;
        }

        const toast = this.createToast(message, type);
        container.appendChild(toast);
        this.activeToasts.push(toast);
        this.animateToast(toast);
    },

    createToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${Config.ICONS[type]}</span>
            <span class="toast-message">${message}</span>
        `;
        return toast;
    },

    animateToast(toast) {
        setTimeout(() => DOM.addClass(toast, 'toast-show'), 10);

        setTimeout(() => {
            DOM.removeClass(toast, 'toast-show');
            setTimeout(() => {
                toast.remove();
                this.activeToasts = this.activeToasts.filter(t => t !== toast);
            }, 300);
        }, Config.TOAST.DISPLAY_TIME);
    },

    showErrorsSequentially(errors, baseMessage = 'Errors:') {
        if (!errors || errors.length === 0) return;

        this.show(baseMessage, 'warning');

        errors.forEach((error, index) => {
            setTimeout(() => {
                this.show(`Error: ${error}`, 'error');
            }, (index + 1) * 800);
        });
    },

    /**
     * Cleanup all active toasts (per memory leak prevention)
     */
    cleanup() {
        this.activeToasts.forEach(toast => {
            if (toast.parentElement) {
                toast.remove();
            }
        });
        this.activeToasts = [];
    }
};

// =========================================================
// Modal Management
// =========================================================
const ModalManager = {
    openModals: [], // Track open modals

    open(modalId) {
        const modal = DOM.get(modalId);
        if (modal) {
            DOM.addClass(modal, 'modal-open');
            document.body.style.overflow = 'hidden';
            this.openModals.push(modalId);
        }
    },

    close(modalId) {
        const modal = DOM.get(modalId);
        if (modal) {
            DOM.removeClass(modal, 'modal-open');
            document.body.style.overflow = '';
            this.openModals = this.openModals.filter(m => m !== modalId);
        }
    },

    /**
     * Close all open modals (per cleanup)
     */
    closeAll() {
        this.openModals.forEach(modalId => this.close(modalId));
    }
};

// =========================================================
// Loader Management (refactored per evitare race conditions)
// =========================================================
const LoaderManager = {
    activeTimeout: null,
    forceHideTimeout: null,
    loaderCount: 0, // Counter per nested show/hide

    show(message = 'Please wait...') {
        const loader = DOM.get('global-loader');
        const messageElement = DOM.get('loader-message');

        if (this.loaderCount === 0) {
            if (messageElement) {
                messageElement.textContent = message;
            }
            if (loader) {
                DOM.addClass(loader, 'active');
                document.body.style.overflow = 'hidden';
            }
        } else {
            // Aggiorna messaggio anche se già visibile
            if (messageElement) {
                messageElement.textContent = message;
            }
        }

        this.loaderCount++;
        this.ensureHiddenAfter(15);
    },

    hide() {
        this.loaderCount = Math.max(0, this.loaderCount - 1);

        if (this.loaderCount === 0) {
            const loader = DOM.get('global-loader');
            if (loader) {
                DOM.removeClass(loader, 'active');
                document.body.style.overflow = '';
            }
        }
    },

    /**
     * Force hide (emergency)
     */
    forceHide() {
        const loader = DOM.get('global-loader');
        if (loader) {
            loader.classList.remove('active');
            loader.style.display = 'none';
            document.body.style.overflow = '';
            console.warn('Loader forcefully hidden');
        }
        this.loaderCount = 0;
    },

    /**
     * Safety net
     */
    ensureHiddenAfter(seconds = 10) {
        if (this.forceHideTimeout) clearTimeout(this.forceHideTimeout);
        
        this.forceHideTimeout = setTimeout(() => {
            const loader = DOM.get('global-loader');
            if (loader && DOM.hasClass(loader, 'active')) {
                console.warn(`Loader still active after ${seconds}s, forcing hide`);
                this.forceHide();
            }
        }, seconds * 1000);
    },

    /**
     * Cleanup
     */
    cleanup() {
        if (this.activeTimeout) {
            clearTimeout(this.activeTimeout);
            this.activeTimeout = null;
        }
        if (this.forceHideTimeout) {
            clearTimeout(this.forceHideTimeout);
            this.forceHideTimeout = null;
        }
        this.loaderCount = 0;
    }
};

const OperationHelper = {
    /**
     * Execute async with loader + safety
     */
    async executeWithLoader(loaderMessage, asyncFunction) {
        LoaderManager.show(loaderMessage);
        
        try {
            const result = await asyncFunction();
            LoaderManager.hide();
            return result;
        } catch (error) {
            LoaderManager.hide();
            throw error;
        }
    },

    /**
     * Execute with monitor (don't close loader)
     */
    async executeWithMonitor(loaderMessage, operationName, asyncFunction) {
        LoaderManager.show(loaderMessage);
        
        try {
            const result = await asyncFunction();
            return result;
        } catch (error) {
            LoaderManager.hide();
            throw error;
        }
    },

    /**
     * Global cleanup
     */
    cleanup() {
        LoaderManager.cleanup();
        ToastManager.cleanup();
        ModalManager.closeAll();
    }
};

// =========================================================
// Confirm Modal Management
// =========================================================
const ConfirmModalManager = {
    resolvePromise: null,

    async show(title, message, type = 'warning') {
        return new Promise((resolve) => {
            const modal = DOM.get('confirmModal');
            const icons = {
                danger: '⚠',
                warning: '⚠',
                info: 'ℹ',
                success: '✓'
            };

            modal.innerHTML = `
                <div class="modal-overlay" onclick="ConfirmModalManager.hide(false)"></div>
                <div class="modal-content modal-small">
                    <div class="modal-header">
                        <h2>${icons[type]} ${title}</h2>
                        <button class="modal-close" onclick="ConfirmModalManager.hide(false)">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="confirm-message">${message}</div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="ConfirmModalManager.hide(false)">
                            Cancel
                        </button>
                        <button class="btn btn-${type}" onclick="ConfirmModalManager.hide(true)">
                            Confirm
                        </button>
                    </div>
                </div>
            `;

            this.resolvePromise = resolve;
            ModalManager.open('confirmModal');
        });
    },

    hide(confirmed) {
        ModalManager.close('confirmModal');
        if (this.resolvePromise) {
            this.resolvePromise(confirmed);
            this.resolvePromise = null;
        }
    }
};

// =========================================================
// Global Window Exports
// =========================================================
window.ToastManager = ToastManager;
window.ModalManager = ModalManager;
window.LoaderManager = LoaderManager;
window.OperationHelper = OperationHelper;
window.ConfirmModalManager = ConfirmModalManager;
window.Utils = Utils;
window.DOM = DOM;
window.Config = Config;

window.showLoader = LoaderManager.show.bind(LoaderManager);
window.hideLoader = LoaderManager.hide.bind(LoaderManager);
window.closeModal = ModalManager.close.bind(ModalManager);
window.openModal = ModalManager.open.bind(ModalManager);
window.showConfirmModal = ConfirmModalManager.show.bind(ConfirmModalManager);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    OperationHelper.cleanup();
});