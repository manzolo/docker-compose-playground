// =========================================================
// SCRIPT INDICATOR MANAGER - Shows script execution AND Docker operation status in cards
// =========================================================

const ScriptIndicatorManager = {
    activeIndicators: new Map(),
    currentPhases: new Map(),  // Track current phase per container to prevent flashing
    hidingContainers: new Set(),  // Track containers being hidden to prevent race conditions

    /**
     * Update script indicators based on operation status
     * Called by OperationMonitor during polling
     */
    updateIndicators(statusData) {
        const scriptsRunning = statusData.scripts_running || [];
        const scriptsCompleted = statusData.scripts_completed || [];

        // Show indicators for running scripts
        scriptsRunning.forEach(script => {
            this.showIndicator(script.container, script.type);
        });

        // Hide indicators for completed scripts
        scriptsCompleted.forEach(script => {
            // Only hide if not in running list anymore
            const stillRunning = scriptsRunning.some(s =>
                s.container === script.container && s.type === script.type
            );
            if (!stillRunning) {
                this.hideIndicator(script.container);
            }
        });

        // NEW: Show Docker operation progress (only if phase changed AND not hiding)
        if (statusData.operation_phase && statusData.container_name) {
            // Ignore updates if we're in the process of hiding this container
            if (this.hidingContainers.has(statusData.container_name)) {
                return;
            }

            const currentPhase = this.currentPhases.get(statusData.container_name);

            // Only update if phase actually changed
            if (currentPhase !== statusData.operation_phase) {
                // For "completed" phase, mark as hiding FIRST to prevent any subsequent updates
                if (statusData.operation_phase === 'completed') {
                    this.hidingContainers.add(statusData.container_name);
                }

                this.currentPhases.set(statusData.container_name, statusData.operation_phase);
                this.showOperationPhase(
                    statusData.container_name,
                    statusData.operation_phase,
                    statusData.operation  // Pass operation type (start, stop, etc.)
                );
            }
        }
    },

    /**
     * Show Docker operation phase (pulling, starting, stopping, etc.)
     */
    showOperationPhase(containerName, phase, operationType = null) {
        // Defensive check: refuse to show if container is being hidden
        if (this.hidingContainers.has(containerName)) {
            return;
        }

        const displayName = ContainerNameUtils.toDisplayName(containerName);
        const card = DOM.query(`[data-name="${displayName}"]`);

        // Map phases to user-friendly messages
        const phaseMap = {
            'removing_existing': { icon: '🗑️', text: 'Removing existing container...' },
            'preparing_volumes': { icon: '📦', text: 'Preparing volumes...' },
            'creating_volumes': { icon: '🔧', text: 'Creating named volumes...' },
            'pulling_image': { icon: '📥', text: 'Pulling Docker image...' },
            'starting_container': { icon: '🐳', text: 'Starting container...' },
            'launching': { icon: '🚀', text: 'Launching container...' },
            'waiting_ready': { icon: '⏳', text: 'Waiting for container to be ready...' },
            'running_post_start': { icon: '📜', text: 'Running post-start script...' },
            'running_pre_stop': { icon: '📜', text: 'Running pre-stop script...' },
            'stopping': { icon: '🛑', text: 'Stopping container...' },
            'removing': { icon: '🗑️', text: 'Removing container...' },
            'completed': { icon: '✅', text: 'Operation completed!' }
        };

        const phaseInfo = phaseMap[phase] || { icon: '⚙️', text: 'Processing...' };

        // Update single container card indicator
        if (card) {
            const indicator = card.querySelector('.script-running-indicator');
            if (indicator) {
                // Don't show "completed" message on single cards - hide immediately
                if (phase === 'completed') {
                    indicator.style.display = 'none';
                    indicator.style.opacity = '1';
                } else {
                    const iconEl = indicator.querySelector('.script-icon');
                    const textEl = indicator.querySelector('.script-text');

                    // Update content
                    if (iconEl) iconEl.textContent = phaseInfo.icon;
                    if (textEl) textEl.textContent = phaseInfo.text;

                    // Only set display/opacity on FIRST show (when currently hidden)
                    // After that, leave it alone to prevent flickering
                    const currentDisplay = window.getComputedStyle(indicator).display;
                    if (currentDisplay === 'none') {
                        indicator.style.opacity = '1';
                        indicator.style.display = 'flex';
                    }
                    // Otherwise indicator is already visible - just content was updated above
                }
            }
        }

        // Update group container tags with blue pulsing dot for Docker operations
        const containerTag = DOM.query(`.container-tag[data-container="${displayName}"]`);
        if (containerTag) {
            const statusDot = containerTag.querySelector('.container-status-dot');

            if (phase === 'completed') {
                // Restore to normal state - infer from operation type
                containerTag.removeAttribute('data-operation-running');
                const isScriptRunning = containerTag.getAttribute('data-script-running') === 'true';

                // Determine if container should be running based on operation type
                const isStartOperation = operationType && (
                    operationType === 'start' ||
                    operationType === 'start_group'
                );
                const isStopOperation = operationType && (
                    operationType === 'stop' ||
                    operationType === 'stop_group'
                );

                // DEBUG: Log operation type to see what we're getting
                console.log('[ScriptIndicator] Completed phase for', displayName, '- operationType:', operationType, 'isStart:', isStartOperation, 'isStop:', isStopOperation);

                if (statusDot) {
                    if (isScriptRunning) {
                        // Keep yellow if script is still running
                        statusDot.style.background = '#f59e0b';
                        statusDot.style.animation = 'pulse-dot 1.5s ease-in-out infinite';
                    } else if (isStartOperation) {
                        // Update single container card status FIRST
                        this.updateSingleCardStatus(displayName, true);

                        // Then update group tag
                        containerTag.setAttribute('data-running', 'true');
                        statusDot.style.background = '#10b981';
                        statusDot.style.animation = 'pulse 2s ease-in-out infinite';

                        // Mark that we've set the final state for this container
                        containerTag.setAttribute('data-final-state-set', 'true');
                    } else if (isStopOperation) {
                        // Update single container card status FIRST
                        this.updateSingleCardStatus(displayName, false);

                        // Then update group tag
                        containerTag.setAttribute('data-running', 'false');
                        statusDot.style.background = '#94a3b8';
                        statusDot.style.animation = 'none';

                        // Mark that we've set the final state for this container
                        containerTag.setAttribute('data-final-state-set', 'true');
                    } else {
                        // Fallback: check current state attribute
                        const isRunning = containerTag.getAttribute('data-running') === 'true';
                        if (isRunning) {
                            statusDot.style.background = '#10b981';
                            statusDot.style.animation = 'pulse 2s ease-in-out infinite';
                        } else {
                            statusDot.style.background = '#94a3b8';
                            statusDot.style.animation = 'none';
                        }
                    }
                }
            } else {
                // Show blue pulsing dot for Docker operations (not script phases)
                const isScriptPhase = phase === 'running_post_start' || phase === 'running_pre_stop';

                if (!isScriptPhase) {
                    containerTag.setAttribute('data-operation-running', 'true');
                    if (statusDot) {
                        statusDot.style.background = '#3b82f6';  // Blue
                        statusDot.style.animation = 'pulse-fast 1s ease-in-out infinite';
                    }
                }
            }
        }

        // Cleanup tracking after completion
        if (phase === 'completed') {
            // hidingContainers already set in updateIndicators() before this call
            // Single container card already hidden immediately above
            // Clean up tracking after a short delay to ensure no race conditions
            setTimeout(() => this.hideIndicator(containerName), 500);
        }
    },

    /**
     * Show script indicator in container card
     */
    showIndicator(containerName, scriptType) {
        // Convert to display name (remove playground- prefix)
        const displayName = ContainerNameUtils.toDisplayName(containerName);

        // 1. Update single container card indicator (if exists)
        const card = DOM.query(`[data-name="${displayName}"]`);
        if (card) {
            const indicator = card.querySelector('.script-running-indicator');
            if (indicator) {
                // Update indicator text based on script type
                const iconEl = indicator.querySelector('.script-icon');
                const textEl = indicator.querySelector('.script-text');

                if (iconEl) iconEl.textContent = '📜';
                if (textEl) {
                    if (scriptType === 'post_start') {
                        textEl.textContent = 'Running post-start script...';
                    } else if (scriptType === 'pre_stop') {
                        textEl.textContent = 'Running pre-stop script...';
                    } else {
                        textEl.textContent = 'Running script...';
                    }
                }

                // Show indicator with proper opacity reset
                indicator.style.opacity = '1';
                indicator.style.display = 'flex';
            }
        }

        // 2. Update container tags in groups (change dot to yellow)
        // Use display name (without 'playground-' prefix) to match data-container attribute
        const containerTag = DOM.query(`.container-tag[data-container="${displayName}"]`);
        if (containerTag) {
            containerTag.setAttribute('data-script-running', 'true');
            // Update inline style to override container-tag-manager styles
            const statusDot = containerTag.querySelector('.container-status-dot');
            if (statusDot) {
                statusDot.style.background = '#f59e0b';
                statusDot.style.animation = 'pulse-dot 1.5s ease-in-out infinite';
            }
        }

        // Track active indicator
        this.activeIndicators.set(containerName, {
            displayName,
            scriptType,
            startedAt: new Date()
        });
    },

    /**
     * Hide script indicator in container card
     */
    hideIndicator(containerName) {
        // Convert to display name (remove playground- prefix)
        const displayName = ContainerNameUtils.toDisplayName(containerName);

        // 1. Hide single container card indicator (if exists)
        const card = DOM.query(`[data-name="${displayName}"]`);
        if (card) {
            const indicator = card.querySelector('.script-running-indicator');
            if (indicator) {
                // Hide immediately without animation to prevent race conditions
                indicator.style.display = 'none';
                indicator.style.opacity = '1';
            }
        }

        // 2. Remove yellow/blue dot from container tags in groups
        // Use display name (without 'playground-' prefix) to match data-container attribute
        const containerTag = DOM.query(`.container-tag[data-container="${displayName}"]`);
        if (containerTag) {
            // Only remove operation/script flags - DON'T touch the final state colors
            // The final state was already set in showOperationPhase() on 'completed' phase
            const wasScriptRunning = containerTag.getAttribute('data-script-running') === 'true';
            const wasDockerOperation = containerTag.getAttribute('data-operation-running') === 'true';

            containerTag.removeAttribute('data-script-running');
            containerTag.removeAttribute('data-operation-running');

            // Only restore colors if this was a SCRIPT operation (not Docker operation)
            // Docker operations already set the final state in showOperationPhase()
            if (wasScriptRunning && !wasDockerOperation) {
                const statusDot = containerTag.querySelector('.container-status-dot');
                const isRunning = containerTag.getAttribute('data-running') === 'true';
                if (statusDot) {
                    if (isRunning) {
                        // Restore green if container is running
                        statusDot.style.background = '#10b981';
                        statusDot.style.animation = 'pulse 2s ease-in-out infinite';
                    } else {
                        // Restore gray if container is stopped
                        statusDot.style.background = '#94a3b8';
                        statusDot.style.animation = 'none';
                    }
                }
            }

            // Don't need to call ContainerTagManager - the data-final-state-set flag
            // will prevent it from overwriting our state on next refresh
        }

        // Remove from all tracking maps/sets
        this.activeIndicators.delete(containerName);
        this.currentPhases.delete(containerName);  // Clear phase tracking
        this.hidingContainers.delete(containerName);  // Clear hiding flag
    },

    /**
     * Hide all active indicators
     */
    hideAllIndicators() {
        this.activeIndicators.forEach((info, containerName) => {
            this.hideIndicator(containerName);
        });
        this.activeIndicators.clear();
        this.currentPhases.clear();  // Clear all phase tracking
        this.hidingContainers.clear();  // Clear all hiding flags
    },

    /**
     * Check if a container has an active indicator
     */
    hasActiveIndicator(containerName) {
        return this.activeIndicators.has(containerName);
    },

    /**
     * Get active indicator info for a container
     */
    getIndicatorInfo(containerName) {
        return this.activeIndicators.get(containerName);
    },

    /**
     * Update single container card status dot
     * This prevents ContainerTagManager from reverting our changes
     */
    updateSingleCardStatus(displayName, isRunning) {
        const card = DOM.query(`.container-card[data-name="${displayName}"]`);
        if (card) {
            const statusDot = card.querySelector('.status-dot');
            if (statusDot) {
                if (isRunning) {
                    statusDot.classList.add('running');
                    statusDot.classList.remove('stopped');
                } else {
                    statusDot.classList.add('stopped');
                    statusDot.classList.remove('running');
                }
            }
        }
    },

    /**
     * Cleanup on page unload
     */
    cleanup() {
        this.hideAllIndicators();
    }
};

window.ScriptIndicatorManager = ScriptIndicatorManager;

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    ScriptIndicatorManager.cleanup();
});
