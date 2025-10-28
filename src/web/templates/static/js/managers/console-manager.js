// =========================================================
// CONSOLE MANAGER - Interactive terminal via WebSocket
// =========================================================

const ConsoleManager = {
    ws: null,
    term: null,
    fitAddon: null,
    webglAddon: null,
    resizeHandler: null, // Track resize handler per cleanup
    container: null, // Track current container

    /**
     * Open console
     */
    open(container, imageName) {
        // Chiudi connessione precedente se esiste
        if (this.ws) {
            this.close();
        }

        this.container = container;
        this.updateConsoleUI(container, '● Connecting...', 'console-connecting');
        ModalManager.open('consoleModal');
        
        // Wait for modal to be fully rendered
        setTimeout(() => {
            this.initializeTerminal();
            this.connectWebSocket(container);
        }, 100);
    },

    /**
     * Update console UI
     */
    updateConsoleUI(container, status, className) {
        const nameEl = DOM.get('consoleContainerName');
        const statusEl = DOM.get('consoleStatus');
        
        if (nameEl) nameEl.textContent = container;
        if (statusEl) {
            statusEl.textContent = status;
            statusEl.className = `console-status ${className}`;
        }
    },

    /**
     * Initialize terminal
     */
    initializeTerminal() {
        if (this.term) {
            this.term.dispose();
            this.term = null;
        }

        if (this.fitAddon) {
            this.fitAddon = null;
        }

        this.term = new Terminal({
            cursorBlink: true,
            wordWrap: true,
            allowProposedApi: true,
            convertEol: true,
            theme: {
                background: '#1e1e1e',
                foreground: '#d4d4d4',
                cursor: '#ffffff',
                selection: '#264f78'
            },
            fontSize: 14,
            fontFamily: '"Cascadia Code", "Fira Code", "Consolas", "Monaco", monospace',
            scrollback: 10000,
            allowTransparency: true
        });

        this.fitAddon = new FitAddon.FitAddon();
        this.term.loadAddon(this.fitAddon);

        // Open terminal in the DOM
        const terminalEl = DOM.get('terminal');
        if (terminalEl) {
            this.term.open(terminalEl);
        }

        // Force initial fit
        try {
            this.fitAddon.fit();
        } catch (e) {
            console.warn('Initial fit failed:', e);
        }

        // Load WebGL addon after fit
        try {
            this.webglAddon = new WebglAddon.WebglAddon();
            this.term.loadAddon(this.webglAddon);

            this.webglAddon.onContextLoss(() => {
                console.warn('WebGL context lost, reinitializing...');
                this.webglAddon.dispose();
                this.webglAddon = new WebglAddon.WebglAddon();
                this.term.loadAddon(this.webglAddon);
            });
        } catch (error) {
            console.warn('WebGL addon not available, using canvas renderer');
        }

        this.term.focus();

        // Handle window resize - rimuovi handler precedente
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
        }

        this.resizeHandler = () => {
            if (this.fitAddon && this.term) {
                try {
                    this.fitAddon.fit();
                    this.term.refresh(0, this.term.rows - 1);
                    if (this.webglAddon && this.webglAddon._renderer) {
                        this.webglAddon._renderer.updateDimensions();
                    }
                } catch (e) {
                    console.warn('Resize fit failed:', e);
                }
            }
        };

        let resizeTimeout;
        const resizeWithDebounce = () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(this.resizeHandler, 250);
        };

        window.addEventListener('resize', resizeWithDebounce);

        // Delayed fit to ensure DOM is ready
        setTimeout(() => {
            if (this.fitAddon && this.term) {
                try {
                    this.fitAddon.fit();
                    this.term.refresh(0, this.term.rows - 1);
                } catch (e) {
                    console.warn('Delayed fit failed:', e);
                }
            }
            if (this.term) {
                this.term.scrollToBottom();
            }
        }, 250);
    },

    /**
     * Connect WebSocket - con proper cleanup
     */
    connectWebSocket(container) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/console/${container}`);

        // Salva i handler originali per cleanup
        const onOpen = () => {
            this.updateConsoleUI(container, '● Connected', 'console-connected');
            this.term.scrollToBottom();
        };

        const onMessage = (event) => {
            let data = event.data;
            
            // Scarta i messaggi di ridimensionamento
            if (data.startsWith('{"type":"resize"')) {
                return;
            }
            
            data = data.replace(/\r?\n/g, '\r\n');
            this.term.write(data);
            this.scrollToBottomIfAtBottom();
            
            if (Math.random() < 0.1) {
                setTimeout(() => {
                    if (this.term) {
                        this.term.refresh(0, this.term.rows - 1);
                    }
                }, 10);
            }
        };

        const onError = (error) => {
            console.error('WebSocket error:', error);
            this.updateConsoleUI(container, '● Error', 'console-error');
            if (this.term) {
                this.term.write('\r\n\x1b[31m✗ Connection error\x1b[0m\r\n');
            }
        };

        const onClose = () => {
            this.updateConsoleUI(container, '● Disconnected', 'console-disconnected');
            if (this.term) {
                this.term.write('\r\n\x1b[33m⚠ Console disconnected\x1b[0m\r\n');
            }
        };

        // Assegna i handler
        this.ws.onopen = onOpen;
        this.ws.onmessage = onMessage;
        this.ws.onerror = onError;
        this.ws.onclose = onClose;

        // Data handler per input da terminale
        if (this.term) {
            this.term.onData(data => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(data);
                }
            });

            // Resize handler per WebSocket
            this.term.onResize((size) => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({
                        type: 'resize',
                        cols: size.cols,
                        rows: size.rows
                    }));
                }
            });
        }
    },

    /**
     * Scroll to bottom if at bottom
     */
    scrollToBottomIfAtBottom() {
        if (!this.term) return;

        const viewport = DOM.query('.xterm-viewport');
        if (!viewport) return;

        const isAtBottom = (viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight) < 10;

        if (isAtBottom) {
            this.term.scrollToBottom();
            setTimeout(() => {
                if (this.term) {
                    this.term.refresh(0, this.term.rows - 1);
                }
            }, 0);
        }
    },

    /**
     * Close console - with proper cleanup
     */
    close() {
        // Chiudi WebSocket
        if (this.ws) {
            this.ws.onopen = null;
            this.ws.onmessage = null;
            this.ws.onerror = null;
            this.ws.onclose = null;
            this.ws.close();
            this.ws = null;
        }

        // Rimuovi resize handler
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
            this.resizeHandler = null;
        }

        // Dispose terminal
        if (this.term) {
            // Rimuovi data handlers
            this.term.onData(() => {});
            this.term.onResize(() => {});
            
            // Dispose WebGL addon se presente
            if (this.webglAddon) {
                try {
                    this.webglAddon.dispose();
                } catch (error) {
                    console.warn('Error disposing WebGL addon:', error);
                }
                this.webglAddon = null;
            }
            
            // Dispose terminal
            this.term.dispose();
            this.term = null;
        }

        this.fitAddon = null;
        this.container = null;
        
        ModalManager.close('consoleModal');
    },

    /**
     * Cleanup su beforeunload
     */
    cleanup() {
        this.close();
    }
};

window.ConsoleManager = ConsoleManager;

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    ConsoleManager.cleanup();
});