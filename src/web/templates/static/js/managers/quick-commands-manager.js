// =========================================================
// QUICK COMMANDS MANAGER - Display and manage quick commands
// =========================================================

const QuickCommandsManager = {
    currentContainer: null,
    currentImageName: null,
    currentCommands: [],

    /**
     * Open from element with data attributes (safer)
     */
    openFromElement(element) {
        const container = element.getAttribute('data-container');
        const image = element.getAttribute('data-image');
        let commandsJson = element.getAttribute('data-commands');
        
        // Debug
        //console.log('Raw commands JSON:', commandsJson);
        
        // Fallback se vuoto
        if (!commandsJson || commandsJson.trim() === '' || commandsJson === '[]' || commandsJson === 'None') {
            commandsJson = '[]';
        }
        
        try {
            const commands = JSON.parse(commandsJson);
            this.open(container, image, commands);
        } catch (e) {
            console.error('Failed to parse commands. Raw:', commandsJson, 'Error:', e);
            ToastManager.show('Error loading commands', 'error');
            // Fallback a array vuoto
            this.open(container, image, []);
        }
    },

    /**
     * Open quick commands modal
     */
    open(container, imageName, commandsData) {
        this.currentContainer = container;
        this.currentImageName = imageName;
        this.currentCommands = commandsData || [];

        const modal = DOM.get('quickCommandsModal');
        if (!modal) {
            ToastManager.show('Quick Commands modal not found', 'error');
            return;
        }

        DOM.get('quickCommandsContainerName').textContent = imageName;
        
        // Render commands
        this.renderCommands();
        
        ModalManager.open('quickCommandsModal');

        // Aggiungi listener per Escape
        if (this.quickCommandsEscapeListener) {
            document.removeEventListener('keydown', this.quickCommandsEscapeListener);
        }

        this.quickCommandsEscapeListener = (e) => {
            if (e.key === 'Escape') {
                e.preventDefault();
                this.close();
            }
        };
        document.addEventListener('keydown', this.quickCommandsEscapeListener);
    },

    /**
     * Render commands list
     */
    renderCommands() {
        const container = DOM.get('quickCommandsList');
        
        if (!this.currentCommands || this.currentCommands.length === 0) {
            container.innerHTML = '<div class="quick-commands-empty"><p>No quick commands available</p></div>';
            return;
        }

        let html = '';
        this.currentCommands.forEach((cmd, index) => {
            // Parse command - può essere stringa o oggetto
            let commandText = '';
            let description = '';
            let isUrl = false;

            if (typeof cmd === 'string') {
                commandText = cmd.trim();
                description = '';
            } else if (typeof cmd === 'object') {
                commandText = cmd.command || cmd.text || '';
                description = cmd.description || cmd.desc || '';
            }

            // Controlla se è un URL (contiene http://, https://, ftp://)
            isUrl = commandText.includes('http://') || commandText.includes('https://') || commandText.includes('ftp://');

            if (commandText) {
                if (isUrl) {
                    // Estrai l'URL dal testo
                    const urlMatch = commandText.match(/https?:\/\/[^\s]+/);
                    const url = urlMatch ? urlMatch[0] : commandText;
                    
                    // Renderizza come link cliccabile diretto CON bottone per aprire
                    html += `
                        <div class="quick-command-item quick-command-url">
                            <div class="quick-command-content" onclick="window.open('${this.escapeAttr(url)}', '_blank')" style="cursor: pointer; flex: 1;">
                                <div class="quick-command-text">${this.escapeHtml(commandText)}</div>
                                ${description ? `<div class="quick-command-description">${this.escapeHtml(description)}</div>` : ''}
                            </div>
                            <div class="quick-command-actions">
                                <button class="quick-command-btn btn-open" 
                                    onclick="event.stopPropagation(); window.open('${this.escapeAttr(url)}', '_blank')"
                                    title="Open URL">
                                    ⚡
                                </button>
                            </div>
                        </div>
                    `;
                } else {
                    // Renderizza come comando - SOLO bottone Copy
                    html += `
                        <div class="quick-command-item">
                            <div class="quick-command-content">
                                <div class="quick-command-text">${this.escapeHtml(commandText)}</div>
                                ${description ? `<div class="quick-command-description">${this.escapeHtml(description)}</div>` : ''}
                            </div>
                            <div class="quick-command-actions">
                                <button class="quick-command-btn btn-copy" 
                                    onclick="event.stopPropagation(); QuickCommandsManager.copyCommand('${this.escapeAttr(commandText)}')"
                                    title="Copy command">
                                    📋
                                </button>
                            </div>
                        </div>
                    `;
                }
            }
        });

        container.innerHTML = html || '<div class="quick-commands-empty"><p>No valid commands</p></div>';
    },

    /**
     * Copy single command to clipboard
     */
    copyCommand(command) {
        navigator.clipboard.writeText(command).then(() => {
            ToastManager.show('Command copied to clipboard!', 'success');
        }).catch(() => {
            ToastManager.show('Failed to copy command', 'error');
        });
    },

    /**
     * Copy all commands to clipboard
     */
    copyAll() {
        if (this.currentCommands.length === 0) {
            ToastManager.show('No commands to copy', 'warning');
            return;
        }

        const allCommands = this.currentCommands
            .map(cmd => typeof cmd === 'string' ? cmd : (cmd.command || cmd.text || ''))
            .filter(cmd => cmd)
            .join('\n');

        navigator.clipboard.writeText(allCommands).then(() => {
            ToastManager.show(`All ${this.currentCommands.length} commands copied!`, 'success');
        }).catch(() => {
            ToastManager.show('Failed to copy commands', 'error');
        });
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
        return String(text).replace(/[&<>"']/g, (m) => map[m]);
    },

    /**
     * Escape for HTML attribute
     */
    escapeAttr(text) {
        return String(text).replace(/'/g, "\\'").replace(/"/g, '&quot;');
    },

    /**
     * Close modal
     */
    close() {
        this.currentContainer = null;
        this.currentImageName = null;
        this.currentCommands = [];

        if (this.quickCommandsEscapeListener) {
            document.removeEventListener('keydown', this.quickCommandsEscapeListener);
        }

        ModalManager.close('quickCommandsModal');
    }
};

window.QuickCommandsManager = QuickCommandsManager;