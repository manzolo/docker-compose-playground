// =========================================================
// DARK MODE MANAGER - Shared across all pages
// =========================================================

const DarkModeManager = {
    STORAGE_KEY: 'darkMode',
    DARK_CLASS: 'dark-mode',
    isInitialized: false,

    /**
     * Early init - Apply dark mode immediately to prevent flash
     * This runs synchronously before page render
     */
    earlyInit() {
        const saved = localStorage.getItem(this.STORAGE_KEY);
        let enableDark = false;

        if (saved !== null) {
            enableDark = saved === 'true';
        } else {
            // Check system preference
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            enableDark = prefersDark;
        }

        // Apply immediately - no DOM manipulation needed
        if (enableDark) {
            document.documentElement.classList.add(this.DARK_CLASS);
        }
    },

    /**
     * Full initialization - Setup interactive features
     * This runs after DOM is ready
     */
    init() {
        if (this.isInitialized) return;
        this.isInitialized = true;

        // Get current dark mode state and sync button icon
        const isDark = document.documentElement.classList.contains(this.DARK_CLASS);
        this.updateToggleButton(isDark);

        this.setupToggleButton();
        this.setupSystemPreference();
    },

    /**
     * Load saved preference or use system preference
     * Note: This is now called by setDarkMode, not needed separately
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

// Run early init immediately to prevent flash
DarkModeManager.earlyInit();

// Run full init when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        DarkModeManager.init();
    });
} else {
    // DOM already loaded, init now
    DarkModeManager.init();
}

window.DarkModeManager = DarkModeManager;