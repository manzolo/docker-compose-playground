// =========================================================
// Dark Mode Manager
// =========================================================

const DarkModeManager = {
    STORAGE_KEY: 'darkMode',
    DARK_CLASS: 'dark-mode',

    /**
     * Inizializza il dark mode
     */
    init() {
        this.loadPreference();
        this.setupToggleButton();
        this.setupSystemPreference();
    },

    /**
     * Carica la preferenza salvata o usa la preferenza di sistema
     */
    loadPreference() {
        const saved = localStorage.getItem(this.STORAGE_KEY);

        if (saved !== null) {
            // Usa la preferenza salvata
            this.setDarkMode(saved === 'true');
        } else {
            // Usa la preferenza di sistema
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.setDarkMode(prefersDark);
        }
    },

    /**
     * Abilita/disabilita il dark mode
     */
    setDarkMode(enabled) {
        if (enabled) {
            document.documentElement.classList.add(this.DARK_CLASS);
        } else {
            document.documentElement.classList.remove(this.DARK_CLASS);
        }

        // Salva la preferenza
        localStorage.setItem(this.STORAGE_KEY, enabled);
        this.updateToggleButton(enabled);
    },

    /**
     * Toggle dark mode
     */
    toggle() {
        const isDark = document.documentElement.classList.contains(this.DARK_CLASS);
        this.setDarkMode(!isDark);
    },

    /**
     * Setup il pulsante di toggle
     */
    setupToggleButton() {
        const button = document.getElementById('darkModeToggle');
        if (button) {
            button.addEventListener('click', () => this.toggle());
        }
    },

    /**
     * Aggiorna il visual del bottone
     */
    updateToggleButton(isDark) {
        const button = document.getElementById('darkModeToggle');
        if (button) {
            const icon = button.querySelector('.dark-mode-icon');
            if (icon) {
                icon.textContent = isDark ? '☀️' : '🌙';
            }
            button.setAttribute('aria-label', isDark ? 'Light mode' : 'Dark mode');
        }
    },

    /**
     * Ascolta i cambiamenti della preferenza di sistema
     */
    setupSystemPreference() {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', (e) => {
            const saved = localStorage.getItem(this.STORAGE_KEY);
            // Solo se l'utente non ha salvato una preferenza
            if (saved === null) {
                this.setDarkMode(e.matches);
            }
        });
    }
};

// Inizializza quando il DOM è pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        DarkModeManager.init();
    });
} else {
    DarkModeManager.init();
}

// Esporta globalmente
window.DarkModeManager = DarkModeManager;