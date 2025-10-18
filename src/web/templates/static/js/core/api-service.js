// =========================================================
// API SERVICE - Centralized API calls
// =========================================================

const ApiService = {
    /**
     * Fetch with timeout
     */
    async fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(
            () => controller.abort(), 
            options.timeout || Config.POLLING.TIMEOUT.START
        );

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    },

    /**
     * Fetch JSON response
     */
    async fetchJson(url, options = {}) {
        const response = await this.fetchWithTimeout(url, options);
        return response.json();
    },

    /**
     * Fetch text response
     */
    async fetchText(url, options = {}) {
        const response = await this.fetchWithTimeout(url, options);
        return response.text();
    },

    /**
     * Fetch blob response (for downloads)
     */
    async fetchBlob(url, options = {}) {
        const response = await this.fetchWithTimeout(url, options);
        return response.blob();
    },

    /**
     * POST request for starting container
     */
    async startContainer(image) {
        return this.fetchJson(`/api/start/${encodeURIComponent(image)}`, {
            method: 'POST',
            timeout: Config.POLLING.TIMEOUT.START
        });
    },

    /**
     * POST request for stopping container
     */
    async stopContainer(containerName) {
        return this.fetchWithTimeout(`/stop/${containerName}`, {
            method: 'POST',
            timeout: Config.POLLING.TIMEOUT.STOP
        });
    },

    /**
     * GET container logs
     */
    async getContainerLogs(containerName) {
        return this.fetchJson(`/logs/${containerName}`);
    },

    /**
     * GET operation status
     */
    async getOperationStatus(operationId) {
        return this.fetchJson(`/api/operation-status/${operationId}`);
    },

    /**
     * POST start group
     */
    async startGroup(groupName) {
        return this.fetchJson(`/api/start-group/${encodeURIComponent(groupName)}`, {
            method: 'POST',
            timeout: Config.POLLING.TIMEOUT.GROUP
        });
    },

    /**
     * POST stop group
     */
    async stopGroup(groupName) {
        return this.fetchJson(`/api/stop-group/${encodeURIComponent(groupName)}`, {
            method: 'POST',
            timeout: Config.POLLING.TIMEOUT.GROUP
        });
    },

    /**
     * POST bulk operations
     */
    async stopAll() {
        return this.fetchJson('/api/stop-all', {
            method: 'POST',
            timeout: Config.POLLING.TIMEOUT.STOP
        });
    },

    async restartAll() {
        return this.fetchJson('/api/restart-all', {
            method: 'POST',
            timeout: Config.POLLING.TIMEOUT.STOP
        });
    },

    async cleanupAll() {
        return this.fetchJson('/api/cleanup-all', {
            method: 'POST',
            timeout: Config.POLLING.TIMEOUT.STOP
        });
    },

    /**
     * Category operations
     */
    async startCategory(category) {
        return this.fetchJson(`/api/start-category/${category}`, {
            method: 'POST'
        });
    },

    async stopCategory(category) {
        return this.fetchJson(`/api/stop-category/${category}`, {
            method: 'POST'
        });
    },

    /**
     * Validation and detection
     */
    async validateImage(imageName) {
        return this.fetchJson('/api/validate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageName })
        });
    },

    async detectShell(imageName) {
        return this.fetchJson('/api/detect-shell', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageName })
        });
    },

    async addContainer(formData) {
        return this.fetchJson('/api/add-container', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
    },

    /**
     * System info
     */
    async getSystemInfo() {
        return this.fetchJson('/api/system-info', {
            timeout: 5000
        });
    },

    /**
     * Backups
     */
    async getBackups() {
        return this.fetchJson('/api/backups');
    },

    async downloadBackup(category, filename) {
        return `${window.location.origin}/api/download-backup/${encodeURIComponent(category)}/${encodeURIComponent(filename)}`;
    },

    /**
     * Export config
     */
    async exportConfig() {
        return this.fetchBlob('/api/export-config');
    },

    /**
     * Server logs
     */
    async getServerLogs() {
        return this.fetchText('/api/logs');
    }
};

window.ApiService = ApiService;