// =========================================================
// EXECUTE COMMAND MANAGER - Run commands in containers
// =========================================================

const ExecuteCommandManager = {
    currentContainer: null,
    autoRefreshInterval: null,
    autoRefreshEnabled: false,
    isFullscreen: false,

    /**
     * Open command executor modal
     */
    open(container, imageName) {
        this.currentContainer = container;

        const modal = DOM.get('commandModal');
        if (!modal) {
            ToastManager.show('Command modal not found', 'error');
            return;
        }

        DOM.get('commandContainerName').textContent = container;
        DOM.get('commandImageName').textContent = imageName;
        DOM.get('commandInput').value = '';
        DOM.get('commandOutput').textContent = '';

        ModalManager.open('commandModal');

        // Invalida cache per l'input (per sicurezza)
        DOM.invalidateCache('commandInput');

        // Focus con delay per assicurare visibilità
        setTimeout(() => {
            const commandInput = DOM.get('commandInput');
            if (commandInput) {
                commandInput.focus();

                // Aggiungi listener per Enter (una sola volta - elemento fresco)
                commandInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        this.executeCommand();
                    }
                });

                // Aggiungi listener per Escape (chiude modal)
                commandInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape') {
                        e.preventDefault();
                        this.close();
                    }
                });
            }
        }, 100);
    },

    /**
     * Execute command
     */
    async executeCommand() {
        const commandInput = DOM.get('commandInput');
        const command = commandInput ? commandInput.value.trim() : '';

        if (!command) {
            ToastManager.show('Please enter a command', 'warning');
            return;
        }

        if (!this.currentContainer) {
            ToastManager.show('No container selected', 'error');
            return;
        }

        const outputArea = DOM.get('commandOutput');
        if (outputArea) {
            outputArea.textContent = 'Executing...';
        }

        showLoader(`Executing command: ${command}`);

        try {
            const response = await fetch(`/api/execute-command/${this.currentContainer}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command: command,
                    timeout: 30
                })
            });

            const result = await response.json();
            hideLoader();

            if (!response.ok) {
                const errorMsg = result.detail || 'Failed to execute command';
                if (outputArea) {
                    outputArea.textContent = `Error: ${errorMsg}`;
                }
                ToastManager.show('Command failed', 'error');
                return;
            }

            // Display output
            const output = result.success
                ? result.output
                : `Command failed with exit code ${result.exit_code}\n${result.output}`;

            if (outputArea) {
                outputArea.textContent = output;
            }

            if (result.success) {
                ToastManager.show('Command executed successfully', 'success');
            } else {
                ToastManager.show(`Command failed (exit code: ${result.exit_code})`, 'warning');
            }

        } catch (error) {
            hideLoader();
            const outputArea = DOM.get('commandOutput');
            if (outputArea) {
                outputArea.textContent = `Error: ${error.message}`;
            }
            ToastManager.show('Error executing command', 'error');
        }
    },

    /**
     * Clear output
     */
    clearOutput() {
        const outputArea = DOM.get('commandOutput');
        const inputArea = DOM.get('commandInput');
        
        if (outputArea) {
            outputArea.textContent = '';
        }
        if (inputArea) {
            inputArea.value = '';
            inputArea.focus();
        }
    },

    /**
     * Copy output to clipboard
     */
    copyOutput() {
        const outputArea = DOM.get('commandOutput');
        const output = outputArea ? outputArea.textContent : '';

        if (!output) {
            ToastManager.show('Nothing to copy', 'warning');
            return;
        }

        navigator.clipboard.writeText(output).then(() => {
            ToastManager.show('Output copied to clipboard', 'success');
        }).catch(() => {
            ToastManager.show('Failed to copy output', 'error');
        });
    },

    /**
     * Open diagnostics
     */
    async openDiagnostics(container, imageName) {
        this.currentContainer = container;

        const modal = DOM.get('diagnosticsModal');
        if (!modal) {
            ToastManager.show('Diagnostics modal not found', 'error');
            return;
        }

        const nameEl = DOM.get('diagnosticsContainerName');
        const imageEl = DOM.get('diagnosticsImageName');

        if (nameEl) nameEl.textContent = container;
        if (imageEl) imageEl.textContent = imageName;

        // Reset auto-refresh to off
        const autoRefreshCheckbox = DOM.get('diagnosticsAutoRefresh');
        if (autoRefreshCheckbox) {
            autoRefreshCheckbox.checked = false;

            // Remove old listener if exists
            if (this.autoRefreshChangeListener) {
                autoRefreshCheckbox.removeEventListener('change', this.autoRefreshChangeListener);
            }

            // Add change listener
            this.autoRefreshChangeListener = (e) => {
                // console.log('Auto-refresh toggled:', e.target.checked);
                this.toggleAutoRefresh(e.target.checked);
            };
            autoRefreshCheckbox.addEventListener('change', this.autoRefreshChangeListener);
        }
        this.stopAutoRefresh();

        // Reset fullscreen state
        this.isFullscreen = false;
        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            DOM.removeClass(modalContent, 'fullscreen');
        }
        this.updateFullscreenButton();

        // Clear all tabs
        DOM.get('diagnosticsProcesses').innerHTML = '';
        DOM.get('diagnosticsDisk').innerHTML = '';
        DOM.get('diagnosticsNetwork').innerHTML = '';
        DOM.get('diagnosticsEnvironment').innerHTML = '';
        DOM.get('diagnosticsUptime').innerHTML = '';
        DOM.get('diagnosticsLogs').innerHTML = '';

        ModalManager.open('diagnosticsModal');

        // Resetta il primo tab come attivo
        DOM.queryAll('.diagnostics-tab-btn').forEach((btn, index) => {
            if (index === 0) {
                DOM.addClass(btn, 'active');
            } else {
                DOM.removeClass(btn, 'active');
            }
        });

        DOM.queryAll('.diagnostics-tab').forEach((tab, index) => {
            tab.style.display = index === 0 ? 'block' : 'none';
        });

        // Rimuovi listener vecchio se esiste
        if (this.diagnosticsEscapeListener) {
            document.removeEventListener('keydown', this.diagnosticsEscapeListener);
        }

        // Aggiungi listener per Escape su document (chiude modal)
        this.diagnosticsEscapeListener = (e) => {
            if (e.key === 'Escape') {
                e.preventDefault();
                this.closeDiagnostics();
            }
        };
        document.addEventListener('keydown', this.diagnosticsEscapeListener);

        // Fetch diagnostics
        this.fetchDiagnostics(container);
    },

    /**
     * Fetch and display diagnostics
     */
    async fetchDiagnostics(container, silent = false) {
        // Only show loader if not auto-refreshing
        if (!silent) {
            showLoader('Running diagnostics...');
        }

        try {
            const response = await fetch(`/api/execute-diagnostic/${container}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();

            if (!silent) {
                hideLoader();
            }

            if (!response.ok) {
                if (!silent) {
                    ToastManager.show('Failed to get diagnostics', 'error');
                }
                return;
            }

            // Display diagnostic data with parsing
            const processesEl = DOM.get('diagnosticsProcesses');
            const diskEl = DOM.get('diagnosticsDisk');
            const networkEl = DOM.get('diagnosticsNetwork');
            const envEl = DOM.get('diagnosticsEnvironment');
            const uptimeEl = DOM.get('diagnosticsUptime');
            const logsEl = DOM.get('diagnosticsLogs');

            // Force invalidate cache to ensure fresh DOM elements
            if (silent) {
                DOM.invalidateCache('diagnosticsProcesses');
                DOM.invalidateCache('diagnosticsDisk');
                DOM.invalidateCache('diagnosticsNetwork');
                DOM.invalidateCache('diagnosticsEnvironment');
                DOM.invalidateCache('diagnosticsUptime');
                DOM.invalidateCache('diagnosticsLogs');
            }

            // Update content
            if (processesEl) {
                processesEl.innerHTML = DiagnosticsParser.parseProcesses(data.diagnostics?.processes || 'N/A');
            }
            if (diskEl) {
                diskEl.innerHTML = DiagnosticsParser.parseDiskUsage(data.diagnostics?.disk_usage || 'N/A');
            }
            if (networkEl) {
                networkEl.innerHTML = DiagnosticsParser.parseNetwork(data.diagnostics?.network || 'N/A');
            }
            if (envEl) {
                envEl.innerHTML = DiagnosticsParser.parseEnvironment(data.diagnostics?.environment || 'N/A');
            }
            if (uptimeEl) {
                uptimeEl.innerHTML = DiagnosticsParser.parseUptime(data.diagnostics?.uptime || 'N/A');
            }
            if (logsEl) {
                logsEl.innerHTML = DiagnosticsParser.parseLogs(data.diagnostics?.recent_logs || 'N/A');
            }

            // Show refresh indicator for silent updates
            if (silent) {
                this.showRefreshIndicator();
            }

            /*if (!silent) {
                ToastManager.show('Diagnostics completed', 'success');
            }*/

        } catch (error) {
            if (!silent) {
                hideLoader();
                ToastManager.show(`Error: ${error.message}`, 'error');
            }
        }
    },

    /**
     * Switch diagnostic tab
     */
    switchTab(tabName) {
        // Hide all tabs
        DOM.queryAll('.diagnostics-tab').forEach(tab => {
            tab.style.display = 'none';
        });

        // Remove active class from buttons
        DOM.queryAll('.diagnostics-tab-btn').forEach(btn => {
            DOM.removeClass(btn, 'active');
        });

        // Show selected tab
        const tabId = `diagnostics${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`;
        const tab = DOM.get(tabId);
        if (tab) {
            tab.style.display = 'block';
        }

        // Add active class to button
        const btn = event.target;
        if (btn) {
            DOM.addClass(btn, 'active');
        }
    },

    /**
     * Close command modal
     */
    close() {
        this.currentContainer = null;
        ModalManager.close('commandModal');
    },

    /**
     * Close diagnostics modal - with proper cleanup
     */
    closeDiagnostics() {
        this.currentContainer = null;

        // Stop auto-refresh
        this.stopAutoRefresh();

        // Exit fullscreen if active
        if (this.isFullscreen) {
            this.isFullscreen = false;
            const modal = DOM.get('diagnosticsModal');
            const modalContent = modal?.querySelector('.modal-content');
            if (modalContent) {
                DOM.removeClass(modalContent, 'fullscreen');
            }
        }

        // Rimuovi listener Escape
        if (this.diagnosticsEscapeListener) {
            document.removeEventListener('keydown', this.diagnosticsEscapeListener);
            this.diagnosticsEscapeListener = null;
        }

        ModalManager.close('diagnosticsModal');
    },

    /**
     * Toggle auto-refresh
     */
    toggleAutoRefresh(enabled) {
        // console.log('toggleAutoRefresh called with:', enabled);
        // console.log('Current container:', this.currentContainer);

        this.autoRefreshEnabled = enabled;

        if (enabled) {
            this.startAutoRefresh();
            //ToastManager.show('Auto-refresh enabled (2s)', 'success');
        } else {
            this.stopAutoRefresh();
            //ToastManager.show('Auto-refresh disabled', 'info');
        }

        this.updateAutoRefreshLabel();
    },

    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
        // console.log('startAutoRefresh called');

        // Clear existing interval if any (but don't change enabled state)
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            // console.log('Cleared existing interval');
        }

        // Set enabled to true
        this.autoRefreshEnabled = true;

        // Set up new interval (2 seconds)
        this.autoRefreshInterval = setInterval(() => {
            // console.log('Auto-refresh tick - enabled:', this.autoRefreshEnabled, 'container:', this.currentContainer);
            if (this.currentContainer && this.autoRefreshEnabled) {
                // console.log('Fetching diagnostics silently...');
                // Silent refresh - don't show loader or toasts
                this.fetchDiagnostics(this.currentContainer, true);
            }
        }, 2000);

        // console.log('Auto-refresh interval started:', this.autoRefreshInterval);
    },

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        // console.log('stopAutoRefresh called');
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            // console.log('Auto-refresh interval cleared');
        }
        this.autoRefreshEnabled = false;
    },

    /**
     * Update auto-refresh label
     */
    updateAutoRefreshLabel() {
        const labelText = DOM.get('diagnosticsAutoRefreshLabel');
        if (labelText) {
            // Keep the refresh indicator element
            const indicator = document.getElementById('diagnosticsRefreshIndicator');
            const indicatorHTML = indicator ? indicator.outerHTML : '<span class="refresh-indicator" id="diagnosticsRefreshIndicator"></span>';

            const baseText = this.autoRefreshEnabled
                ? 'Auto-refresh (2s) - ON '
                : 'Auto-refresh (2s) ';

            labelText.innerHTML = baseText + indicatorHTML;
        }
    },

    /**
     * Toggle fullscreen mode
     */
    toggleFullscreen() {
        this.isFullscreen = !this.isFullscreen;

        const modal = DOM.get('diagnosticsModal');
        const modalContent = modal?.querySelector('.modal-content');

        if (!modalContent) return;

        if (this.isFullscreen) {
            DOM.addClass(modalContent, 'fullscreen');
            //ToastManager.show('Fullscreen mode enabled', 'success');
        } else {
            DOM.removeClass(modalContent, 'fullscreen');
            //ToastManager.show('Fullscreen mode disabled', 'info');
        }

        this.updateFullscreenButton();
    },

    /**
     * Update fullscreen button icon
     */
    updateFullscreenButton() {
        const btn = DOM.get('diagnosticsFullscreenBtn');
        if (btn) {
            btn.textContent = this.isFullscreen ? '⛶' : '⛶';
            btn.title = this.isFullscreen ? 'Exit fullscreen' : 'Toggle fullscreen';
        }
    },

    /**
     * Show visual indicator when auto-refresh updates
     */
    showRefreshIndicator() {
        const indicator = DOM.get('diagnosticsRefreshIndicator');
        if (!indicator) return;

        // Add pulse animation
        indicator.textContent = '●';
        indicator.classList.add('pulse');

        // Remove after animation
        setTimeout(() => {
            indicator.classList.remove('pulse');
            setTimeout(() => {
                indicator.textContent = '';
            }, 200);
        }, 500);
    },

    /**
     * Cleanup su beforeunload
     */
    cleanup() {
        this.close();
        this.closeDiagnostics();
    }
};

window.ExecuteCommandManager = ExecuteCommandManager;

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    ExecuteCommandManager.cleanup();
});