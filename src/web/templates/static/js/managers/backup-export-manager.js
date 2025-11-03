// =========================================================
// BACKUP & EXPORT MANAGER - Manage backups and exports
// =========================================================

const BackupExportManager = {
    currentBackups: [], // Store the current list of backups
    currentSort: { key: 'modified', direction: 'desc' }, // Default sort

    /**
     * Show backups modal
     */
    async showBackups() {
        try {
            showLoader('Loading backups...');
            DOM.invalidateCache('backupFilterInput');
            DOM.invalidateCache('backupsTable');
            const data = await ApiService.getBackups();
            this.currentBackups = data.backups;
            this.sortBackups(this.currentSort.key, true);
            ModalManager.open('backupsModal');
            
            requestAnimationFrame(() => {
                const filterInput = DOM.get('backupFilterInput');
                if (filterInput) {
                    filterInput.focus();
                }
            });

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
        this.currentBackups = backups;
        const list = DOM.get('backupsList');
        if (!list) return;

        if (!backups || backups.length === 0) {
            list.innerHTML = this.createEmptyState();
        } else {
            list.innerHTML = this.createBackupsTable(backups);
            this.updateSortIndicators();
        }
    },

    /**
     * Create empty state HTML
     */
    createEmptyState() {
        return `
            <div class="backups-empty">
                <div class="backups-empty-icon">📦</div>
                <div class="backups-empty-text">No backups found</div>
                <div class="backups-empty-hint">Backups will appear here when available</div>
            </div>
        `;
    },

    /**
     * Create backups table HTML
     */
    createBackupsTable(backups) {
        // Calculate stats
        const totalCount = backups.length;
        const totalSize = backups.reduce((sum, backup) => sum + backup.size, 0);

        // Create table rows with proper CSS classes
        const rows = backups.map(backup => `
            <tr>
                <td data-label="Container">
                    <span class="backup-category">${backup.container}</span>
                </td>
                <td data-label="File">
                    <span class="backup-filename">${backup.file}</span>
                </td>
                <td data-label="Size">
                    <span class="backup-size">${this.formatFileSize(backup.size)}</span>
                </td>
                <td data-label="Modified">
                    <span class="backup-date">${new Date(backup.modified * 1000).toLocaleString()}</span>
                </td>
                <td data-label="Actions">
                    <button class="backup-download-btn" onclick="BackupExportManager.downloadBackup('${backup.container}', '${backup.file}')">
                        Download
                    </button>
                    <button class="backup-delete-btn" onclick="BackupExportManager.deleteBackup('${backup.container}', '${backup.file}')">
                        Delete
                    </button>
                </td>
            </tr>
        `).join('');

        return `
            <div class="backups-stats">
                <div class="backups-stats-item">
                    <span class="backups-stats-icon">📦</span>
                    <span>Total Backups:</span>
                    <span class="backups-stats-value">${totalCount}</span>
                </div>
                <div class="backups-stats-item">
                    <span class="backups-stats-icon">💾</span>
                    <span>Total Size:</span>
                    <span class="backups-stats-value">${this.formatFileSize(totalSize)}</span>
                </div>
            </div>
            <div class="backup-filter">
                <input type="text" id="backupFilterInput" onkeyup="BackupExportManager.filterBackups()" placeholder="Filter by container...">
            </div>
            <div class="backups-table-wrapper">
                <table class="backups-table" id="backupsTable">
                    <thead>
                        <tr>
                            <th class="sortable" data-sort-key="container" onclick="BackupExportManager.sortBackups('container')">Container</th>
                            <th class="sortable" data-sort-key="file" onclick="BackupExportManager.sortBackups('file')">File</th>
                            <th class="sortable" data-sort-key="size" onclick="BackupExportManager.sortBackups('size')">Size</th>
                            <th class="sortable" data-sort-key="modified" onclick="BackupExportManager.sortBackups('modified')">Modified</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
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
     * Sort backups table
     */
    sortBackups(sortKey, keepDirection = false) {
        const filterInput = DOM.get('backupFilterInput');
        const filterValue = filterInput ? filterInput.value : '';

        if (!keepDirection) {
            if (this.currentSort.key === sortKey) {
                this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                this.currentSort.key = sortKey;
                this.currentSort.direction = 'asc';
            }
        }

        const sortedBackups = [...this.currentBackups].sort((a, b) => {
            const valA = a[this.currentSort.key];
            const valB = b[this.currentSort.key];

            if (valA < valB) {
                return this.currentSort.direction === 'asc' ? -1 : 1;
            }
            if (valA > valB) {
                return this.currentSort.direction === 'asc' ? 1 : -1;
            }
            return 0;
        });

        this.renderBackupsList(sortedBackups);
        this.updateSortIndicators();

        DOM.invalidateCache('backupFilterInput');
        DOM.invalidateCache('backupsTable');

        if (filterValue) {
            const newFilterInput = DOM.get('backupFilterInput');
            if (newFilterInput) {
                newFilterInput.value = filterValue;
                this.filterBackups();
            }
        }
    },

    /**
     * Update sort indicators in table headers
     */
    updateSortIndicators() {
        const headers = document.querySelectorAll('#backupsTable th[data-sort-key]');
        headers.forEach(header => {
            const key = header.getAttribute('data-sort-key');
            header.classList.remove('sort-asc', 'sort-desc');
            if (key === this.currentSort.key) {
                header.classList.add(this.currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        });
    },

    /**
     * Filter backups table
     */
    filterBackups() {
        const input = DOM.get('backupFilterInput');
        const filter = input.value.toUpperCase();
        const table = DOM.get('backupsTable');
        const tr = table.getElementsByTagName('tr');

        for (let i = 1; i < tr.length; i++) {
            const td = tr[i].getElementsByTagName('td')[0];
            if (td) {
                const txtValue = td.textContent || td.innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    tr[i].style.display = '';
                } else {
                    tr[i].style.display = 'none';
                }
            }
        }
    },

    /**
     * Download backup
     */
    async downloadBackup(container, filename) {
        try {
            const url = await ApiService.downloadBackup(container, filename);
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
     * Delete backup
     */
    async deleteBackup(container, filename) {
        const confirmation = await ConfirmModalManager.show(
            'Delete Backup',
            `Are you sure you want to delete the backup: <strong>${filename}</strong>? This action cannot be undone.`,
            'danger'
        );

        if (confirmation) {
            try {
                showLoader(`Deleting ${filename}...`);

                const filterInput = DOM.get('backupFilterInput');
                const filterValue = filterInput ? filterInput.value : '';

                await ApiService.deleteBackup(container, filename);
                ToastManager.show('Backup deleted successfully', 'success');
                
                await this.showBackups();

                if (filterValue) {
                    DOM.invalidateCache('backupFilterInput');
                    DOM.invalidateCache('backupsTable');
                    const newFilterInput = DOM.get('backupFilterInput');
                    if (newFilterInput) {
                        newFilterInput.value = filterValue;
                        this.filterBackups();
                    }
                }

            } catch (error) {
                ToastManager.show(`Delete failed: ${error.message}`, 'error');
            } finally {
                hideLoader();
            }
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