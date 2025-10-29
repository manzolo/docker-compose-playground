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
    messageBuffer: [], // Buffer for batching writes
    bufferTimer: null, // Timer for flushing buffer
    lastScrollCheck: 0, // Throttle scroll checks
    isAtBottom: true, // Track scroll position

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

            // Discard resize messages
            if (data.startsWith('{"type":"resize"')) {
                return;
            }

            // Add to buffer for batched processing
            this.addToBuffer(data);
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
     * Add message to buffer for batched writing (improves performance)
     */
    addToBuffer(data) {
        this.messageBuffer.push(data);

        // Clear existing timer
        if (this.bufferTimer) {
            clearTimeout(this.bufferTimer);
        }

        // Flush immediately if buffer is large, otherwise wait a bit for more messages
        if (this.messageBuffer.length >= 10) {
            this.flushBuffer();
        } else {
            this.bufferTimer = setTimeout(() => this.flushBuffer(), 16); // ~60fps
        }
    },

    /**
     * Flush buffered messages to terminal
     */
    flushBuffer() {
        if (!this.term || this.messageBuffer.length === 0) return;

        // Join all buffered messages
        const data = this.messageBuffer.join('');
        this.messageBuffer = [];
        this.bufferTimer = null;

        // Write to terminal (xterm.js handles newlines correctly)
        this.term.write(data);

        // Throttled scroll check (max once per 100ms)
        const now = Date.now();
        if (now - this.lastScrollCheck > 100) {
            this.lastScrollCheck = now;
            this.checkAndScroll();
        }
    },

    /**
     * Check scroll position and scroll to bottom if needed
     */
    checkAndScroll() {
        if (!this.term) return;

        const viewport = DOM.query('.xterm-viewport');
        if (!viewport) return;

        // Check if user is at bottom
        const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
        this.isAtBottom = distanceFromBottom < 50;

        // Auto-scroll if at bottom
        if (this.isAtBottom) {
            this.term.scrollToBottom();
        }
    },

    /**
     * Close console - with proper cleanup
     */
    close() {
        // Flush any remaining buffered messages
        if (this.bufferTimer) {
            clearTimeout(this.bufferTimer);
            this.bufferTimer = null;
        }
        if (this.messageBuffer.length > 0) {
            this.flushBuffer();
        }

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