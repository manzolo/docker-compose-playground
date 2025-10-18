// =========================================================
// SYSTEM INFO MANAGER - Display system information
// =========================================================

const SystemInfoManager = {
    systemInfoInterval: null,
    debounceTimer: null,
    isInitialized: false,
    inProgress: false,

    /**
     * Initialize system info manager
     */
    initialize() {
        if (this.isInitialized) return;

        this.isInitialized = true;
        this.load();

        if (this.systemInfoInterval) {
            clearInterval(this.systemInfoInterval);
        }

        this.systemInfoInterval = setInterval(
            () => this.load(),
            30000
        );
    },

    /**
     * Load system information
     */
    async load() {
        if (this.inProgress || this.debounceTimer) {
            return;
        }

        this.debounceTimer = setTimeout(() => {
            this.debounceTimer = null;
        }, 2000);

        try {
            const data = await ApiService.getSystemInfo();
            this.updateUI(data);
        } catch (error) {
            this.handleError(error);
        }
    },

    /**
     * Update UI with system info
     */
    updateUI(data) {
        this.updateElementText('stat-total', data.counts.total);
        this.updateElementText('stat-running', data.counts.running);
        this.updateElementText('stat-stopped', data.counts.stopped);

        this.updateElementText('docker-info',
            `Version: ${data.docker.version}\nContainers: ${data.docker.containers}\nImages: ${data.docker.images}`);

        this.updateElementText('network-info',
            `Name: ${data.network.name}\nDriver: ${data.network.driver}\nSubnet: ${data.network.subnet || 'N/A'}`);

        this.updateElementText('volume-info',
            `Path: ${data.volume.path}\nSize: ${data.volume.size || 'N/A'}`);

        this.updateActiveContainers(data.active_containers);
    },

    /**
     * Update element text content
     */
    updateElementText(elementId, text) {
        const element = DOM.get(elementId);
        if (element) {
            element.textContent = text;
        }
    },

    /**
     * Update active containers list
     */
    updateActiveContainers(containers) {
        const activeList = DOM.get('active-list');
        if (!activeList) return;

        if (!containers || containers.length === 0) {
            activeList.innerHTML = '<p style="color: #64748b;">No active containers</p>';
        } else {
            activeList.innerHTML = containers.map(container =>
                `<div class="active-container-item">
                    <span>🐳 ${container.name}</span>
                    <span class="container-status">${container.status}</span>
                </div>`
            ).join('');
        }
    },

    /**
     * Handle error
     */
    handleError(error) {
        if (error.name === 'AbortError') {
            console.error('SystemInfoManager: Timeout after 5s');
        } else {
            console.error('SystemInfoManager: Failed to load system info:', error);
        }
    },

    /**
     * Pause updates
     */
    pause() {
        this.inProgress = true;
        if (this.systemInfoInterval) {
            clearInterval(this.systemInfoInterval);
            this.systemInfoInterval = null;
        }
    },

    /**
     * Resume updates
     */
    resume() {
        this.inProgress = false;
        if (!this.systemInfoInterval) {
            this.systemInfoInterval = setInterval(
                () => this.load(),
                30000
            );
        }
        this.load();
    },

    /**
     * Cleanup
     */
    cleanup() {
        if (this.systemInfoInterval) {
            clearInterval(this.systemInfoInterval);
            this.systemInfoInterval = null;
        }
    }
};

window.SystemInfoManager = SystemInfoManager;