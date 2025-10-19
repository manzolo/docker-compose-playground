// =========================================================
// MONITORING STATS MANAGER - Real-time container stats
// =========================================================

const MonitoringStatsManager = {
    statsIntervals: {},
    statsData: {},

    /**
     * Start monitoring a container
     */
    async startMonitoring(container) {
        if (this.statsIntervals[container]) {
            return; // Already monitoring
        }

        // Initial fetch
        await this.fetchStats(container);

        // Set up polling
        this.statsIntervals[container] = setInterval(() => {
            this.fetchStats(container);
        }, 2000); // Update every 2 seconds
    },

    /**
     * Stop monitoring a container
     */
    stopMonitoring(container) {
        if (this.statsIntervals[container]) {
            clearInterval(this.statsIntervals[container]);
            delete this.statsIntervals[container];
        }
    },

    /**
     * Fetch container stats
     */
    async fetchStats(container) {
        try {
            const response = await fetch(`/api/container-stats/${container}`);
            
            if (!response.ok) {
                if (response.status === 400) {
                    // Container not running
                    this.stopMonitoring(container);
                }
                return;
            }

            const stats = await response.json();
            this.statsData[container] = stats;
            this.updateStatsUI(container, stats);

        } catch (error) {
            console.error('Error fetching stats for', container, ':', error);
        }
    },

    /**
     * Update stats UI
     */
    updateStatsUI(container, stats) {
        const statsPanel = DOM.get(`stats-panel-${container}`);
        if (!statsPanel) return;

        // CPU
        const cpuPercent = stats.cpu.percent;
        const cpuBar = statsPanel.querySelector('.stat-cpu-bar');
        const cpuText = statsPanel.querySelector('.stat-cpu-text');
        if (cpuBar) {
            cpuBar.style.width = Math.min(cpuPercent, 100) + '%';
            cpuBar.style.background = this.getColorForPercent(cpuPercent);
        }
        if (cpuText) {
            cpuText.textContent = `${cpuPercent.toFixed(1)}% (${stats.cpu.cores} cores)`;
        }

        // Memory
        const memPercent = stats.memory.percent;
        const memBar = statsPanel.querySelector('.stat-memory-bar');
        const memText = statsPanel.querySelector('.stat-memory-text');
        if (memBar) {
            memBar.style.width = Math.min(memPercent, 100) + '%';
            memBar.style.background = this.getColorForPercent(memPercent);
        }
        if (memText) {
            memText.textContent = `${stats.memory.usage_mb}MB / ${stats.memory.limit_mb}MB (${memPercent.toFixed(1)}%)`;
        }

        // Network
        const netText = statsPanel.querySelector('.stat-network-text');
        if (netText) {
            netText.textContent = `↓ ${stats.network.rx_mb}MB | ↑ ${stats.network.tx_mb}MB`;
        }

        // I/O
        const ioText = statsPanel.querySelector('.stat-io-text');
        if (ioText) {
            ioText.textContent = `R: ${stats.io.read_mb}MB | W: ${stats.io.write_mb}MB`;
        }

        // Processes
        const procText = statsPanel.querySelector('.stat-processes-text');
        if (procText) {
            procText.textContent = `${stats.processes} processes`;
        }
    },

    /**
     * Get color based on percentage
     */
    getColorForPercent(percent) {
        if (percent < 33) return '#10b981'; // Green
        if (percent < 66) return '#f59e0b'; // Orange
        return '#ef4444'; // Red
    },

    /**
     * Get stats data for container
     */
    getStats(container) {
        return this.statsData[container] || null;
    },

    /**
     * Stop all monitoring
     */
    stopAllMonitoring() {
        Object.keys(this.statsIntervals).forEach(container => {
            this.stopMonitoring(container);
        });
    }
};

window.MonitoringStatsManager = MonitoringStatsManager;