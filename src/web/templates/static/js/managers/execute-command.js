// =========================================================
// EXECUTE COMMAND MANAGER - Run commands in containers
// =========================================================

const ExecuteCommandManager = {
    currentContainer: null,

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
    async fetchDiagnostics(container) {
        showLoader('Running diagnostics...');

        try {
            const response = await fetch(`/api/execute-diagnostic/${container}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            hideLoader();

            if (!response.ok) {
                ToastManager.show('Failed to get diagnostics', 'error');
                return;
            }

            // Display diagnostic data with parsing
            const processesEl = DOM.get('diagnosticsProcesses');
            const diskEl = DOM.get('diagnosticsDisk');
            const networkEl = DOM.get('diagnosticsNetwork');
            const envEl = DOM.get('diagnosticsEnvironment');
            const uptimeEl = DOM.get('diagnosticsUptime');
            const logsEl = DOM.get('diagnosticsLogs');

            if (processesEl) processesEl.innerHTML = DiagnosticsParser.parseProcesses(data.diagnostics?.processes || 'N/A');
            if (diskEl) diskEl.innerHTML = DiagnosticsParser.parseDiskUsage(data.diagnostics?.disk_usage || 'N/A');
            if (networkEl) networkEl.innerHTML = DiagnosticsParser.parseNetwork(data.diagnostics?.network || 'N/A');
            if (envEl) envEl.innerHTML = DiagnosticsParser.parseEnvironment(data.diagnostics?.environment || 'N/A');
            if (uptimeEl) uptimeEl.innerHTML = DiagnosticsParser.parseUptime(data.diagnostics?.uptime || 'N/A');
            if (logsEl) logsEl.innerHTML = DiagnosticsParser.parseLogs(data.diagnostics?.recent_logs || 'N/A');

            ToastManager.show('Diagnostics completed', 'success');

        } catch (error) {
            hideLoader();
            ToastManager.show(`Error: ${error.message}`, 'error');
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
        
        // Rimuovi listener Escape
        if (this.diagnosticsEscapeListener) {
            document.removeEventListener('keydown', this.diagnosticsEscapeListener);
            this.diagnosticsEscapeListener = null;
        }
        
        ModalManager.close('diagnosticsModal');
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