// =========================================================
// MOTD MANAGER - Message of the Day display and interaction
// =========================================================

const MOTDManager = {
    /**
     * Toggle MOTD section
     */
    toggle(header) {
        const content = header.nextElementSibling;
        const icon = header.querySelector('.motd-toggle-icon');

        DOM.toggleClass(content, 'open');
        DOM.toggleClass(icon, 'open');
    },

    /**
     * Copy MOTD text to clipboard
     */
    copy(button) {
        const motdText = button.parentElement.parentElement.querySelector('.motd-text');
        const text = motdText.textContent;

        navigator.clipboard.writeText(text).then(() => {
            const originalText = button.textContent;
            button.textContent = '✓ Copied!';

            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);

            ToastManager.show('Commands copied to clipboard!', 'success');
        }).catch(() => {
            ToastManager.show('Failed to copy commands', 'error');
        });
    },

    /**
     * Send MOTD to console
     */
    async sendToConsole(containerName) {
        if (!ConsoleManager.term || ConsoleManager.ws?.readyState !== WebSocket.OPEN) {
            ToastManager.show('Console not connected. Open the console first.', 'warning');
            ConsoleManager.open(containerName, '');
            return;
        }

        const motdText = event.target.parentElement.parentElement.querySelector('.motd-text').textContent;
        ConsoleManager.ws.send(motdText + '\n');

        ToastManager.show('Commands sent to console!', 'success');
    }
};

window.MOTDManager = MOTDManager;