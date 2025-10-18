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
            GROUP: 10000
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
// DOM Helper
// =========================================================
const DOM = {
    get(id) {
        return document.getElementById(id);
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
    
    addClass(element, className) {
        if (element) element.classList.add(className);
    },
    
    removeClass(element, className) {
        if (element) element.classList.remove(className);
    },
    
    toggleClass(element, className) {
        if (element) element.classList.toggle(className);
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

        const poll = async () => {
            try {
                const response = await fetch(`/api/operation-status/${operationId}`);
                const statusData = await response.json();

                if (messageFormatter) {
                    showLoader(messageFormatter(statusData));
                }

                if (statusData.status === 'completed' || statusData.status === 'error') {
                    hideLoader();
                    return statusData;
                }

                attempts++;
                if (attempts < maxAttempts) {
                    return new Promise(resolve => 
                        setTimeout(() => resolve(poll()), interval)
                    );
                } else {
                    throw new Error(`Operation timed out after ${maxAttempts} attempts`);
                }
            } catch (error) {
                console.error('Polling error:', error);
                attempts++;
                if (attempts < maxAttempts) {
                    return new Promise(resolve => 
                        setTimeout(() => resolve(poll()), interval)
                    );
                } else {
                    throw error;
                }
            }
        };

        return poll();
    }
};

// =========================================================
// Toast Notification System
// =========================================================
const ToastManager = {
    show(message, type = 'info') {
        const container = DOM.get('toast-container');
        if (!container) {
            console.warn('Toast container is missing. Message:', message);
            return;
        }

        const toast = this.createToast(message, type);
        container.appendChild(toast);
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
            setTimeout(() => toast.remove(), 300);
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
    }
};

// =========================================================
// Modal Management
// =========================================================
const ModalManager = {
    open(modalId) {
        const modal = DOM.get(modalId);
        if (modal) {
            DOM.addClass(modal, 'modal-open');
            document.body.style.overflow = 'hidden';
        }
    },

    close(modalId) {
        const modal = DOM.get(modalId);
        if (modal) {
            DOM.removeClass(modal, 'modal-open');
            document.body.style.overflow = '';
        }
    }
};

// =========================================================
// Loader Management
// =========================================================
const LoaderManager = {
    show(message = 'Please wait...') {
        const loader = DOM.get('global-loader');
        const messageElement = DOM.get('loader-message');

        if (messageElement) {
            messageElement.textContent = message;
        }

        if (loader) {
            DOM.addClass(loader, 'active');
            document.body.style.overflow = 'hidden';
        } else {
            console.error('Loader element not found!');
            ToastManager.show(`Operation in progress: ${message}`, 'info');
        }
    },

    hide() {
        const loader = DOM.get('global-loader');
        if (loader) {
            DOM.removeClass(loader, 'active');
            document.body.style.overflow = '';
        } else {
            console.error('Loader element not found!');
        }
    }
};

// =========================================================
// Confirm Modal Management
// =========================================================
const ConfirmModalManager = {
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
window.ConfirmModalManager = ConfirmModalManager;
window.Utils = Utils;
window.DOM = DOM;
window.Config = Config;

window.showLoader = LoaderManager.show.bind(LoaderManager);
window.hideLoader = LoaderManager.hide.bind(LoaderManager);
window.closeModal = ModalManager.close.bind(ModalManager);
window.openModal = ModalManager.open.bind(ModalManager);
window.showConfirmModal = ConfirmModalManager.show.bind(ConfirmModalManager);