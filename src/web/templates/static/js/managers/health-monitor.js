// =========================================================
// HEALTH MONITOR MANAGER - System health and diagnostics
// =========================================================

const HealthMonitorManager = {
    healthCheckInterval: null,
    isInitialized: false,

    /**
     * Initialize health monitor
     */
    init() {
        if (this.isInitialized) return;
        this.isInitialized = true;

        // Initial check
        this.checkSystemHealth();

        // Set up polling every 30 seconds
        this.healthCheckInterval = setInterval(() => {
            this.checkSystemHealth();
        }, 30000);
    },

    /**
     * Check system health
     */
    async checkSystemHealth() {
        try {
            const response = await fetch('/api/system-health');
            const health = await response.json();

            this.updateHealthUI(health);
            this.updateWarnings(health);
        } catch (error) {
            console.error('Error checking system health:', error);
        }
    },

    /**
     * Update health UI
     */
    updateHealthUI(health) {
        const statusBadge = DOM.get('system-health-status');
        if (statusBadge) {
            statusBadge.textContent = health.status.toUpperCase();
            statusBadge.className = `badge badge-status-${health.status}`;
        }

        // Update metrics
        if (health.metrics.docker) {
            this.updateMetric('docker-version', health.metrics.docker.version);
            this.updateMetric('docker-containers', health.metrics.docker.containers_running);
            this.updateMetric('docker-memory', health.metrics.docker.memory_available_gb + ' GB');
        }

        if (health.metrics.containers) {
            this.updateMetric('containers-total', health.metrics.containers.total);
            this.updateMetric('containers-running', health.metrics.containers.running);
            this.updateMetric('containers-stopped', health.metrics.containers.stopped);
        }

        if (health.metrics.disk) {
            const diskPercent = health.metrics.disk.percent_used;
            this.updateDiskBar(diskPercent, health.metrics.disk.free_gb);
        }

        if (health.metrics.volume) {
            this.updateMetric('volume-size', health.metrics.volume.size_gb + ' GB');
        }
    },

    /**
     * Update single metric
     */
    updateMetric(elementId, value) {
        const el = DOM.get(elementId);
        if (el) {
            el.textContent = value;
        }
    },

    /**
     * Update disk usage bar
     */
    updateDiskBar(percent, freeGb) {
        const bar = DOM.get('disk-usage-bar');
        if (bar) {
            bar.style.width = Math.min(percent, 100) + '%';
            
            if (percent < 60) {
                bar.style.background = '#10b981'; // Green
            } else if (percent < 80) {
                bar.style.background = '#f59e0b'; // Orange
            } else {
                bar.style.background = '#ef4444'; // Red
            }
        }

        const text = DOM.get('disk-usage-text');
        if (text) {
            text.textContent = `${percent.toFixed(1)}% used (${freeGb.toFixed(2)} GB free)`;
        }
    },

    /**
     * Update warnings display
     */
    updateWarnings(health) {
        const warningsContainer = DOM.get('health-warnings');
        if (!warningsContainer) return;

        warningsContainer.innerHTML = '';

        // Display critical alerts
        if (health.critical && health.critical.length > 0) {
            const criticalDiv = document.createElement('div');
            criticalDiv.className = 'health-alert alert-critical';
            criticalDiv.innerHTML = `
                <span class="alert-icon">⚠️</span>
                <div class="alert-content">
                    <strong>Critical Issues:</strong>
                    <ul>${health.critical.map(c => `<li>${c}</li>`).join('')}</ul>
                </div>
            `;
            warningsContainer.appendChild(criticalDiv);
        }

        // Display warnings
        if (health.warnings && health.warnings.length > 0) {
            const warningDiv = document.createElement('div');
            warningDiv.className = 'health-alert alert-warning';
            warningDiv.innerHTML = `
                <span class="alert-icon">⚠️</span>
                <div class="alert-content">
                    <strong>Warnings:</strong>
                    <ul>${health.warnings.map(w => `<li>${w}</li>`).join('')}</ul>
                </div>
            `;
            warningsContainer.appendChild(warningDiv);
        }

        // Display recommendations
        if (health.recommendations && health.recommendations.length > 0) {
            const recDiv = document.createElement('div');
            recDiv.className = 'health-alert alert-info';
            recDiv.innerHTML = `
                <span class="alert-icon">💡</span>
                <div class="alert-content">
                    <strong>Recommendations:</strong>
                    <ul>${health.recommendations.map(r => `<li>${r}</li>`).join('')}</ul>
                </div>
            `;
            warningsContainer.appendChild(recDiv);
        }
    },

    /**
     * Check port conflicts
     */
    async checkPortConflicts() {
        showLoader('Checking for port conflicts...');

        try {
            const response = await fetch('/api/port-conflicts');
            const data = await response.json();
            hideLoader();

            if (!response.ok) {
                ToastManager.show('Failed to check port conflicts', 'error');
                return;
            }

            this.showPortConflictsModal(data);
        } catch (error) {
            hideLoader();
            ToastManager.show(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Show port conflicts modal
     */
    showPortConflictsModal(data) {
        const modal = DOM.get('portConflictsModal');
        if (!modal) return;

        let content = `
            <div class="port-conflicts-info">
                <p>Status: <strong>${data.status === 'ok' ? '✓ No conflicts' : '⚠️ Conflicts detected'}</strong></p>
                <p>Ports in use: <code>${data.ports_in_use.join(', ') || 'None'}</code></p>
            </div>
        `;

        if (data.container_conflicts && data.container_conflicts.length > 0) {
            content += '<div class="port-conflicts-section"><h4>Container Conflicts:</h4><ul>';
            data.container_conflicts.forEach(conflict => {
                content += `<li>Port <code>${conflict.port}</code>: ${conflict.containers.join(', ')}</li>`;
            });
            content += '</ul></div>';
        }

        if (data.system_conflicts && data.system_conflicts.length > 0) {
            content += '<div class="port-conflicts-section"><h4>System Conflicts:</h4><ul>';
            data.system_conflicts.forEach(conflict => {
                content += `<li>Port <code>${conflict.port}</code>: System process</li>`;
            });
            content += '</ul></div>';
        }

        const contentArea = modal.querySelector('.modal-body');
        if (contentArea) {
            contentArea.innerHTML = content;
        }

        ModalManager.open('portConflictsModal');
    },

    /**
     * Validate container config
     */
    async validateContainerConfig(imageName) {
        showLoader(`Validating configuration for ${imageName}...`);

        try {
            const response = await fetch(`/api/validate-config/${imageName}`);
            const validation = await response.json();
            hideLoader();

            if (!response.ok) {
                ToastManager.show('Failed to validate configuration', 'error');
                return;
            }

            this.showValidationResults(validation);
        } catch (error) {
            hideLoader();
            ToastManager.show(`Error: ${error.message}`, 'error');
        }
    },

    /**
     * Show validation results modal
     */
    showValidationResults(validation) {
        const modal = DOM.get('validationModal');
        if (!modal) return;

        const titleEl = modal.querySelector('h2');
        if (titleEl) {
            titleEl.textContent = `Configuration Validation: ${validation.image}`;
        }

        let content = `
            <div class="validation-status">
                <strong>Status: ${validation.valid ? '✓ Valid' : '✗ Invalid'}</strong>
            </div>
        `;

        if (validation.errors && validation.errors.length > 0) {
            content += '<div class="validation-section errors"><h4>Errors:</h4><ul>';
            validation.errors.forEach(error => {
                content += `<li class="error-item">${error}</li>`;
            });
            content += '</ul></div>';
        }

        if (validation.warnings && validation.warnings.length > 0) {
            content += '<div class="validation-section warnings"><h4>Warnings:</h4><ul>';
            validation.warnings.forEach(warning => {
                content += `<li class="warning-item">${warning}</li>`;
            });
            content += '</ul></div>';
        }

        const contentArea = modal.querySelector('.modal-body');
        if (contentArea) {
            contentArea.innerHTML = content;
        }

        ModalManager.open('validationModal');

        if (validation.valid) {
            ToastManager.show('Configuration is valid', 'success');
        } else {
            ToastManager.show('Configuration has errors', 'error');
        }
    },

    /**
     * Cleanup
     */
    cleanup() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
        this.isInitialized = false;
    }
};

window.HealthMonitorManager = HealthMonitorManager;