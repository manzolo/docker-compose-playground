// =========================================================
// CONSOLE MANAGER - Interactive terminal via WebSocket
// =========================================================

const ConsoleManager = {
    ws: null,
    term: null,
    fitAddon: null,
    webglAddon: null,

    /**
     * Open console
     */
    open(container, imageName) {
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
        DOM.get('consoleContainerName').textContent = container;
        const statusElement = DOM.get('consoleStatus');
        statusElement.textContent = status;
        statusElement.className = `console-status ${className}`;
    },

    /**
     * Initialize terminal
     */
    initializeTerminal() {
        if (this.term) {
            this.term.dispose();
            this.term = null;
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
        this.term.open(DOM.get('terminal'));

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

        // Handle window resize
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                if (this.fitAddon && this.term) {
                    try {
                        this.fitAddon.fit();
                        this.term.refresh(0, this.term.rows - 1);
                        // Ensure WebGL context is updated
                        if (this.webglAddon) {
                            this.webglAddon._renderer?.updateDimensions();
                        }
                    } catch (e) {
                        console.warn('Resize fit failed:', e);
                    }
                }
            }, 250);
        });

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
            this.term.scrollToBottom();
        }, 250);
    },

    /**
     * Connect WebSocket
     */
    connectWebSocket(container) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/console/${container}`);

        this.ws.onopen = () => {
            this.updateConsoleUI(container, '● Connected', 'console-connected');
            // Removed term.write to avoid displaying in terminal
            // this.term.write('\r\n\x1b[32m✓ Connected to console\x1b[0m\r\n\r\n');
            this.term.scrollToBottom();
        };

        this.ws.onmessage = (event) => {
            let data = event.data;
            
            // Scarta i messaggi di ridimensionamento (non devono essere visualizzati)
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

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConsoleUI(container, '● Error', 'console-error');
            this.term.write('\r\n\x1b[31m✗ Connection error\x1b[0m\r\n');
        };

        this.ws.onclose = () => {
            this.updateConsoleUI(container, '● Disconnected', 'console-disconnected');
            if (this.term) {
                this.term.write('\r\n\x1b[33m⚠ Console disconnected\x1b[0m\r\n');
            }
        };

        this.term.onData(data => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(data);
            }
        });

        this.term.onResize((size) => {
            //console.debug('Terminal resized:', size.cols, size.rows); // Debugging
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'resize',
                    cols: size.cols,
                    rows: size.rows
                }));
            }
        });
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
     * Close console
     */
    close() {
        if (this.ws) {
            this.ws.onclose = null;
            this.ws.close();
            this.ws = null;
        }

        if (this.term) {
            if (this.webglAddon) {
                try {
                    this.webglAddon.dispose();
                } catch (error) {
                    console.warn('Error disposing WebGL addon:', error);
                }
                this.webglAddon = null;
            }
            this.term.dispose();
            this.term = null;
        }

        this.fitAddon = null;
        ModalManager.close('consoleModal');
    }
};

window.ConsoleManager = ConsoleManager;