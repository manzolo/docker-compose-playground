// =========================================================
// CONTAINER NAME UTILS - Standardize container naming
// =========================================================

/**
 * Utility for consistent container name handling across frontend
 *
 * Backend (Docker) uses full names with 'playground-' prefix
 * Frontend displays short names without prefix
 *
 * Examples:
 *   - Full name: "playground-php-8.4"
 *   - Display name: "php-8.4"
 */
const ContainerNameUtils = {
    /**
     * Convert to full Docker container name (with playground- prefix)
     * @param {string} name - Container name (with or without prefix)
     * @returns {string} Full container name with playground- prefix
     */
    toFullName(name) {
        if (!name) return '';
        return name.startsWith('playground-') ? name : `playground-${name}`;
    },

    /**
     * Convert to display name (without playground- prefix)
     * @param {string} name - Container name (with or without prefix)
     * @returns {string} Display name without playground- prefix
     */
    toDisplayName(name) {
        if (!name) return '';
        return name.replace(/^playground-/, '');
    },

    /**
     * Check if name has playground- prefix
     * @param {string} name - Container name to check
     * @returns {boolean} True if name starts with playground-
     */
    hasPrefix(name) {
        if (!name) return false;
        return name.startsWith('playground-');
    },

    /**
     * Normalize name to display format (ensures consistent format)
     * Removes prefix if present
     * @param {string} name - Container name
     * @returns {string} Normalized display name
     */
    normalize(name) {
        return this.toDisplayName(name);
    },

    /**
     * Extract image name from container name
     * Alias for toDisplayName for clarity in some contexts
     * @param {string} containerName - Full or partial container name
     * @returns {string} Image/display name
     */
    toImageName(containerName) {
        return this.toDisplayName(containerName);
    }
};

// Export to window for global access
window.ContainerNameUtils = ContainerNameUtils;
