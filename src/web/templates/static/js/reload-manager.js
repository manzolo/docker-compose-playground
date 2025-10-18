// =========================================================
// RELOAD MANAGER - Handle page reloads with countdown
// =========================================================

const ReloadManager = {
    reloadTimeoutId: null,
    reloadToastId: null,
    countdownInterval: null,

    /**
     * Show reload toast with countdown
     * @param {number} delayMs - Delay before reload in milliseconds
     */
    showReloadToast(delayMs = 5000) {
        const delaySeconds = Math.ceil(delayMs / 1000);
        let secondsLeft = delaySeconds;

        const container = DOM.get('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = 'toast toast-info reload-toast';
        toast.innerHTML = `
            <span class="toast-icon">↻</span>
            <div class="toast-content">
                <span class="toast-message">Page reloading in <strong id="countdown">${secondsLeft}s</strong></span>
                <button class="toast-cancel-btn" onclick="ReloadManager.cancelReload()">Cancel</button>
            </div>
        `;

        container.appendChild(toast);
        setTimeout(() => DOM.addClass(toast, 'toast-show'), 10);

        this.countdownInterval = setInterval(() => {
            secondsLeft--;
            const countdownEl = toast.querySelector('#countdown');
            if (countdownEl) {
                countdownEl.textContent = `${secondsLeft}s`;
            }

            if (secondsLeft <= 0) {
                clearInterval(this.countdownInterval);
            }
        }, 1000);

        this.reloadTimeoutId = setTimeout(() => {
            this.performReload(toast);
        }, delayMs);

        this.reloadToastId = toast;
    },

    /**
     * Cancel scheduled reload
     */
    cancelReload() {
        if (this.reloadTimeoutId) {
            clearTimeout(this.reloadTimeoutId);
            this.reloadTimeoutId = null;
        }

        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }

        if (this.reloadToastId) {
            const toast = this.reloadToastId;
            DOM.removeClass(toast, 'toast-show');
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 300);
            this.reloadToastId = null;
        }

        ToastManager.show('✓ Reload cancelled', 'info');
    },

    /**
     * Perform actual reload
     */
    performReload(toast) {
        if (toast && toast.parentElement) {
            toast.remove();
        }
        location.reload();
    }
};

window.ReloadManager = ReloadManager;