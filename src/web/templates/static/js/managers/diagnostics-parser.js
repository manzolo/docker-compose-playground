// =========================================================
// DIAGNOSTICS PARSER - Convert raw output to tables
// =========================================================

const DiagnosticsParser = {
    /**
     * Parse processes output (ps aux format) into table
     */
    parseProcesses(rawOutput) {
        if (!rawOutput || rawOutput === 'N/A') return '<p class="no-data">No process data available</p>';

        const lines = rawOutput.trim().split('\n');
        if (lines.length < 2) return `<p class="no-data">Invalid process data</p>`;

        // Get headers from first line
        const headers = lines[0].split(/\s+/);
        const rows = lines.slice(1);

        let html = '<table class="diagnostics-table"><thead><tr>';
        headers.forEach(header => {
            html += `<th>${this.escapeHtml(header)}</th>`;
        });
        html += '</tr></thead><tbody>';

        rows.forEach((row, index) => {
            const cells = row.split(/\s+/);
            html += '<tr>';
            headers.forEach((_, i) => {
                const cellValue = cells[i] || '';
                html += `<td>${this.escapeHtml(cellValue)}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        return html;
    },

    /**
     * Parse disk usage output into table
     */
    parseDiskUsage(rawOutput) {
        if (!rawOutput || rawOutput === 'N/A') return '<p class="no-data">No disk data available</p>';

        const lines = rawOutput.trim().split('\n');
        if (lines.length < 2) return `<p class="no-data">Invalid disk data</p>`;

        // Get headers from first line
        const headers = lines[0].split(/\s+/);
        const rows = lines.slice(1);

        let html = '<table class="diagnostics-table"><thead><tr>';
        headers.forEach(header => {
            html += `<th>${this.escapeHtml(header)}</th>`;
        });
        html += '</tr></thead><tbody>';

        rows.forEach((row) => {
            if (row.trim()) {
                const cells = row.split(/\s+/);
                html += '<tr>';
                headers.forEach((_, i) => {
                    const cellValue = cells[i] || '';
                    // Aggiungi classe per le percentuali
                    const isPercentage = cellValue.includes('%');
                    html += `<td ${isPercentage ? 'class="percentage"' : ''}>${this.escapeHtml(cellValue)}</td>`;
                });
                html += '</tr>';
            }
        });

        html += '</tbody></table>';
        return html;
    },

    /**
     * Parse network connections into table
     */
    parseNetwork(rawOutput) {
        if (!rawOutput || rawOutput === 'N/A') return '<p class="no-data">No network data available</p>';

        const lines = rawOutput.trim().split('\n');
        if (lines.length < 2) return `<p class="no-data">Invalid network data</p>`;

        // Get headers from first line
        const headers = lines[0].split(/\s+/);
        const rows = lines.slice(1);

        let html = '<table class="diagnostics-table"><thead><tr>';
        headers.forEach(header => {
            html += `<th>${this.escapeHtml(header)}</th>`;
        });
        html += '</tr></thead><tbody>';

        rows.forEach((row) => {
            if (row.trim()) {
                const cells = row.split(/\s+/);
                html += '<tr>';
                headers.forEach((_, i) => {
                    const cellValue = cells[i] || '';
                    html += `<td>${this.escapeHtml(cellValue)}</td>`;
                });
                html += '</tr>';
            }
        });

        html += '</tbody></table>';
        return html;
    },

    /**
     * Parse environment variables into table
     */
    parseEnvironment(rawOutput) {
        if (!rawOutput || rawOutput === 'N/A') return '<p class="no-data">No environment data available</p>';

        const lines = rawOutput.trim().split('\n');
        let html = '<table class="diagnostics-table"><thead><tr><th>Variable</th><th>Value</th></tr></thead><tbody>';

        lines.forEach((line) => {
            if (line.trim()) {
                const [key, ...valueParts] = line.split('=');
                const value = valueParts.join('=');
                html += `<tr><td class="env-key">${this.escapeHtml(key || 'N/A')}</td><td class="env-value">${this.escapeHtml(value || '')}</td></tr>`;
            }
        });

        html += '</tbody></table>';
        return html;
    },

    /**
     * Parse uptime info into readable format
     */
    parseUptime(rawOutput) {
        if (!rawOutput || rawOutput === 'N/A') return '<p class="no-data">No uptime data available</p>';

        const lines = rawOutput.trim().split('\n');
        let html = '<div class="uptime-info">';

        lines.forEach((line) => {
            if (line.trim()) {
                const [key, ...valueParts] = line.split(':');
                const value = valueParts.join(':').trim();
                html += `<div class="uptime-item"><strong>${this.escapeHtml(key)}:</strong> <span>${this.escapeHtml(value)}</span></div>`;
            }
        });

        html += '</div>';
        return html;
    },

    /**
     * Parse logs into formatted output
     */
    parseLogs(rawOutput) {
        if (!rawOutput || rawOutput === 'N/A') return '<p class="no-data">No logs available</p>';

        const lines = rawOutput.trim().split('\n');
        let html = '<pre class="logs-output">';

        lines.forEach((line) => {
            // Aggiungi colore per i livelli di log
            if (line.includes('ERROR') || line.includes('CRITICAL')) {
                html += `<span class="log-error">${this.escapeHtml(line)}</span>\n`;
            } else if (line.includes('WARNING')) {
                html += `<span class="log-warning">${this.escapeHtml(line)}</span>\n`;
            } else if (line.includes('INFO') || line.includes('DEBUG')) {
                html += `<span class="log-info">${this.escapeHtml(line)}</span>\n`;
            } else {
                html += `${this.escapeHtml(line)}\n`;
            }
        });

        html += '</pre>';
        return html;
    },

    /**
     * Escape HTML special characters
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }
};

window.DiagnosticsParser = DiagnosticsParser;