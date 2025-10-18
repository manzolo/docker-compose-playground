// =========================================================
// BACKUP & EXPORT MANAGER - Manage backups and exports
// =========================================================

const BackupExportManager = {
    /**
     * Show backups modal
     */
    async showBackups() {
        try {
            showLoader('Loading backups...');
            const data = await ApiService.getBackups();
            this.renderBackupsList(data.backups);
            ModalManager.open('backupsModal');
        } catch (error) {
            ToastManager.show(`Error loading backups: ${error.message}`, 'error');
        } finally {
            hideLoader();
        }
    },

    /**
     * Render backups list
     */
    renderBackupsList(backups) {
        const list = DOM.get('backupsList');
        if (!list) return;

        if (!backups || backups.length === 0) {
            list.innerHTML = '<p style="color: #64748b;">No backups found</p>';
        } else {
            list.innerHTML = this.createBackupsTable(backups);
        }
    },

    /**
     * Create backups table HTML
     */
    createBackupsTable(backups) {
        const rows = backups.map(backup => `
            <tr>
                <td>${backup.category}</td>
                <td>${backup.file}</td>
                <td>${this.formatFileSize(backup.size)}</td>
                <td>${new Date(backup.modified * 1000).toLocaleString()}</td>
                <td><button class="btn btn-primary btn-sm" onclick="BackupExportManager.downloadBackup('${backup.category}', '${backup.file}')">Download</button></td>
            </tr>
        `).join('');

        return `
            <table class="backups-table">
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>File</th>
                        <th>Size</th>
                        <th>Modified</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    },

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes >= 1024 * 1024) {
            return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        } else if (bytes >= 1024) {
            return (bytes / 1024).toFixed(2) + ' KB';
        } else {
            return bytes + ' bytes';
        }
    },

    /**
     * Download backup
     */
    async downloadBackup(category, filename) {
        try {
            const url = await ApiService.downloadBackup(category, filename);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            ToastManager.show(`Downloading ${filename}...`, 'info');
        } catch (error) {
            ToastManager.show(`Download failed: ${error.message}`, 'error');
        }
    },

    /**
     * Export configuration
     */
    async exportConfig() {
        try {
            ToastManager.show('Exporting configuration...', 'info');

            const blob = await ApiService.exportConfig();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `playground-config-${new Date().toISOString().split('T')[0]}.yml`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            ToastManager.show('Configuration exported', 'success');
        } catch (error) {
            ToastManager.show(`Export failed: ${error.message}`, 'error');
        }
    },

    /**
     * Show server logs
     */
    async showServerLogs() {
        try {
            showLoader('Loading server logs...');
            const logs = await ApiService.getServerLogs();
            DOM.get('logContent').textContent = logs || 'No logs available';
            ModalManager.open('logModal');
        } catch (error) {
            ToastManager.show(`Error loading logs: ${error.message}`, 'error');
        } finally {
            hideLoader();
        }
    }
};

window.BackupExportManager = BackupExportManager;
window.showBackups = BackupExportManager.showBackups.bind(BackupExportManager);
window.downloadBackup = BackupExportManager.downloadBackup.bind(BackupExportManager);
window.exportConfig = BackupExportManager.exportConfig.bind(BackupExportManager);
window.showServerLogs = BackupExportManager.showServerLogs.bind(BackupExportManager);