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
        return this.fetchJson(`/stop/${encodeURIComponent(containerName)}`, {
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

    async cleanupContainer(containerName) {
        return this.fetchJson(`/api/cleanup/${encodeURIComponent(containerName)}`, {
            method: 'POST',
            timeout: Config.POLLING.TIMEOUT.CLEANUP
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
    },
    /**
     * Server logs
     */
    async getServerLogs() {
        return this.fetchText('/api/logs');
    },

    /**
     * Container statistics
     */
    async getContainerStats(container) {
        return this.fetchJson(`/api/container-stats/${container}`, {
            timeout: 10000
        });
    },

    /**
     * System health
     */
    async getSystemHealth() {
        return this.fetchJson('/api/system-health', {
            timeout: 10000
        });
    },

    /**
     * Container health status
     */
    async getContainersHealth() {
        return this.fetchJson('/api/containers-health', {
            timeout: 10000
        });
    },

    /**
     * Port conflicts check
     */
    async checkPortConflicts() {
        return this.fetchJson('/api/port-conflicts', {
            timeout: 10000
        });
    },

    /**
     * Execute command in container
     */
    async executeCommand(container, command, timeout = 30) {
        return this.fetchJson(`/api/execute-command/${container}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command, timeout }),
            timeout: (timeout + 5) * 1000
        });
    },

    /**
     * Run diagnostics on container
     */
    async runDiagnostics(container) {
        return this.fetchJson(`/api/execute-diagnostic/${container}`, {
            timeout: 6000
        });
    },

    /**
     * Validate container configuration
     */
    async validateContainerConfig(image) {
        return this.fetchJson(`/api/validate-config/${image}`, {
            timeout: 10000
        });
    }
};

window.ApiService = ApiService;