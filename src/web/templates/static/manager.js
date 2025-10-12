// Toast system (reuse from main)
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = { success: '✓', error: '✗', info: 'ℹ', warning: '⚠' };
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('toast-show'), 10);
    setTimeout(() => {
        toast.classList.remove('toast-show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Start by category
async function startByCategory() {
    const category = prompt('Enter category name (linux, programming, database, etc.):');
    if (!category) return;
    
    showToast(`Starting all containers in category: ${category}...`, 'info');
    
    try {
        const response = await fetch(`/api/start-category/${category}`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Started ${data.started} containers in ${category}`, 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showToast(data.detail || 'Failed to start category', 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// Stop all containers
async function stopAll() {
    if (!confirm('Stop ALL running containers?')) return;
    
    showToast('Stopping all containers...', 'info');
    
    try {
        const response = await fetch('/api/stop-all', { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Stopped ${data.stopped} containers`, 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showToast('Failed to stop all containers', 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// Restart all containers
async function restartAll() {
    if (!confirm('Restart ALL running containers?')) return;
    
    showToast('Restarting all containers...', 'info');
    
    try {
        const response = await fetch('/api/restart-all', { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Restarted ${data.restarted} containers`, 'success');
            setTimeout(() => location.reload(), 3000);
        } else {
            showToast('Failed to restart containers', 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// Cleanup all
async function cleanupAll() {
    const confirmed = confirm('⚠️ DANGER: This will STOP and REMOVE ALL playground containers!\n\nAre you absolutely sure?');
    if (!confirmed) return;
    
    const doubleCheck = confirm('This action cannot be undone. Type YES to confirm.');
    if (!doubleCheck) return;
    
    showToast('Cleaning up all containers...', 'warning');
    
    try {
        const response = await fetch('/api/cleanup-all', { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Cleaned up ${data.removed} containers`, 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showToast('Cleanup failed', 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// Start category
async function startCategory(category) {
    if (!confirm(`Start all containers in category: ${category}?`)) return;
    
    showToast(`Starting ${category} containers...`, 'info');
    
    try {
        const response = await fetch(`/api/start-category/${category}`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Started ${data.started} containers`, 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showToast('Failed to start category', 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// View category
function viewCategory(category) {
    window.location.href = `/?category=${category}`;
}

// Export configuration
async function exportConfig() {
    showToast('Exporting configuration...', 'info');
    
    try {
        const response = await fetch('/api/export-config');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `playground-config-${new Date().toISOString().split('T')[0]}.yml`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showToast('Configuration exported', 'success');
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

// View logs
async function viewLogs() {
    window.open('/api/logs', '_blank');
}

// Export backups
function exportBackups() {
    window.location.href = '/api/backups';
}

// Load system info
async function loadSystemInfo() {
    try {
        const response = await fetch('/api/system-info');
        const data = await response.json();
        
        document.getElementById('docker-info').textContent = 
            `Version: ${data.docker.version}\nContainers: ${data.docker.containers}\nImages: ${data.docker.images}`;
        
        document.getElementById('network-info').textContent = 
            `Name: ${data.network.name}\nDriver: ${data.network.driver}\nSubnet: ${data.network.subnet || 'N/A'}`;
        
        document.getElementById('volume-info').textContent = 
            `Path: ${data.volume.path}\nSize: ${data.volume.size || 'N/A'}`;
        
        // Active containers list
        const activeList = document.getElementById('active-list');
        if (data.active_containers.length === 0) {
            activeList.innerHTML = '<p style="color: #64748b;">No active containers</p>';
        } else {
            activeList.innerHTML = data.active_containers.map(c => 
                `<div class="active-container-item">
                    <span>🐳 ${c.name}</span>
                    <span class="container-status">${c.status}</span>
                </div>`
            ).join('');
        }
    } catch (e) {
        console.error('Failed to load system info:', e);
    }
}

// Load on page ready
document.addEventListener('DOMContentLoaded', () => {
    loadSystemInfo();
    
    // Refresh stats every 10 seconds
    setInterval(loadSystemInfo, 10000);
});