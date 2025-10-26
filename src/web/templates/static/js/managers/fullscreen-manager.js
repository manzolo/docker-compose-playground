// =========================================================
// FULLSCREEN MANAGER - Toggle fullscreen for logs and console
// =========================================================
const FullscreenManager = {
    logFullscreenActive: false,
    consoleFullscreenActive: false,

    /**
     * Toggle log fullscreen
     */
    toggleLogFullscreen() {
        const modal = DOM.get('logModal');
        const content = modal.querySelector('.modal-content');
        this.logFullscreenActive = !this.logFullscreenActive;
        if (this.logFullscreenActive) {
            DOM.addClass(content, 'fullscreen');
            this.updateFullscreenButton('logFullscreenBtn', true);
        } else {
            DOM.removeClass(content, 'fullscreen');
            this.updateFullscreenButton('logFullscreenBtn', false);
        }
    },

    /**
     * Toggle console fullscreen
     */
    toggleConsoleFullscreen() {
        const modal = DOM.get('consoleModal');
        const content = modal.querySelector('.modal-content');
        this.consoleFullscreenActive = !this.consoleFullscreenActive;
        if (this.consoleFullscreenActive) {
            DOM.addClass(content, 'fullscreen');
            this.updateFullscreenButton('consoleFullscreenBtn', true);
        } else {
            DOM.removeClass(content, 'fullscreen');
            this.updateFullscreenButton('consoleFullscreenBtn', false);

            // Focus back to term when exiting fullscreen (like in initializeTerminal)
            setTimeout(() => {
                if (ConsoleManager.term) {
                    ConsoleManager.term.focus();
                }
            }, 50);
        }
        setTimeout(() => {
            if (ConsoleManager.fitAddon) {
                ConsoleManager.fitAddon.fit();
                ConsoleManager.term.focus();
            }
        }, 100);
    },

    /**
     * Update fullscreen button visual
     */
    updateFullscreenButton(buttonId, isFullscreen) {
        const btn = DOM.get(buttonId);
        if (btn) {
            if (isFullscreen) {
                btn.textContent = '⊕';
                btn.title = 'Exit fullscreen';
                btn.style.transform = 'scale(1.2)';
            } else {
                btn.textContent = '⊡';
                btn.title = 'Enter fullscreen';
                btn.style.transform = 'scale(1)';
            }
        }
    }
};

window.FullscreenManager = FullscreenManager;