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
        setTimeout(() => {
            DOM.get('commandInput').focus();
        }, 100);
    },

    /**
     * Execute command
     */
    async executeCommand() {
        const command = DOM.get('commandInput').value.trim();
        
        if (!command) {
            ToastManager.show('Please enter a command', 'warning');
            return;
        }

        if (!this.currentContainer) {
            ToastManager.show('No container selected', 'error');
            return;
        }

        const outputArea = DOM.get('commandOutput');
        outputArea.textContent = 'Executing...';

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
                outputArea.textContent = `Error: ${result.detail || 'Failed to execute command'}`;
                ToastManager.show('Command failed', 'error');
                return;
            }

            // Display output
            const output = result.success 
                ? result.output 
                : `Command failed with exit code ${result.exit_code}\n${result.output}`;
            
            outputArea.textContent = output;
            
            if (result.success) {
                ToastManager.show('Command executed successfully', 'success');
            } else {
                ToastManager.show(`Command failed (exit code: ${result.exit_code})`, 'warning');
            }

        } catch (error) {
            hideLoader();
            outputArea.textContent = `Error: ${error.message}`;
            ToastManager.show('Error executing command', 'error');
        }
    },

    /**
     * Clear output
     */
    clearOutput() {
        DOM.get('commandOutput').textContent = '';
        DOM.get('commandInput').value = '';
        DOM.get('commandInput').focus();
    },

    /**
     * Copy output to clipboard
     */
    copyOutput() {
        const output = DOM.get('commandOutput').textContent;
        
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

        DOM.get('diagnosticsContainerName').textContent = container;
        DOM.get('diagnosticsImageName').textContent = imageName;
        
        // Clear all tabs
        DOM.get('diagnosticsProcesses').textContent = '';
        DOM.get('diagnosticsDisk').textContent = '';
        DOM.get('diagnosticsNetwork').textContent = '';
        DOM.get('diagnosticsEnvironment').textContent = '';
        DOM.get('diagnosticsUptime').textContent = '';
        DOM.get('diagnosticsLogs').textContent = '';

        ModalManager.open('diagnosticsModal');
        
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

            // Display diagnostic data
            DOM.get('diagnosticsProcesses').textContent = data.diagnostics.processes || 'N/A';
            DOM.get('diagnosticsDisk').textContent = data.diagnostics.disk_usage || 'N/A';
            DOM.get('diagnosticsNetwork').textContent = data.diagnostics.network || 'N/A';
            DOM.get('diagnosticsEnvironment').textContent = data.diagnostics.environment || 'N/A';
            DOM.get('diagnosticsUptime').textContent = data.diagnostics.uptime || 'N/A';
            DOM.get('diagnosticsLogs').textContent = data.diagnostics.recent_logs || 'N/A';

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
        const tab = DOM.get(`diagnostics${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
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
     * Close diagnostics modal
     */
    closeDiagnostics() {
        this.currentContainer = null;
        ModalManager.close('diagnosticsModal');
    }
};

window.ExecuteCommandManager = ExecuteCommandManager;