// =========================================================
// DARK MODE MANAGER - Shared across all pages
// =========================================================

const DarkModeManager = {
    STORAGE_KEY: 'darkMode',
    DARK_CLASS: 'dark-mode',

    /**
     * Initialize dark mode
     */
    init() {
        this.loadPreference();
        this.setupToggleButton();
        this.setupSystemPreference();
    },

    /**
     * Load saved preference or use system preference
     */
    loadPreference() {
        const saved = localStorage.getItem(this.STORAGE_KEY);

        if (saved !== null) {
            this.setDarkMode(saved === 'true');
        } else {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.setDarkMode(prefersDark);
        }
    },

    /**
     * Enable/disable dark mode
     */
    setDarkMode(enabled) {
        if (enabled) {
            DOM.addClass(document.documentElement, this.DARK_CLASS);
        } else {
            DOM.removeClass(document.documentElement, this.DARK_CLASS);
        }

        localStorage.setItem(this.STORAGE_KEY, enabled);
        this.updateToggleButton(enabled);
    },

    /**
     * Toggle dark mode
     */
    toggle() {
        const isDark = DOM.hasClass(document.documentElement, this.DARK_CLASS);
        this.setDarkMode(!isDark);
    },

    /**
     * Setup toggle button
     */
    setupToggleButton() {
        const button = DOM.get('darkModeToggle');
        if (button) {
            DOM.on(button, 'click', () => this.toggle());
        }
    },

    /**
     * Update toggle button visual
     */
    updateToggleButton(isDark) {
        const button = DOM.get('darkModeToggle');
        if (button) {
            const icon = button.querySelector('.dark-mode-icon');
            if (icon) {
                icon.textContent = isDark ? '☀️' : '🌙';
            }
            button.setAttribute('aria-label', isDark ? 'Light mode' : 'Dark mode');
        }
    },

    /**
     * Listen for system preference changes
     */
    setupSystemPreference() {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', (e) => {
            const saved = localStorage.getItem(this.STORAGE_KEY);
            if (saved === null) {
                this.setDarkMode(e.matches);
            }
        });
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        DarkModeManager.init();
    });
} else {
    DarkModeManager.init();
}

window.DarkModeManager = DarkModeManager;