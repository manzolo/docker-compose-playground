let currentStep = 1;
const totalSteps = 3;

// Toast system
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

// Step Navigation
function nextStep() {
    if (!validateCurrentStep()) {
        return;
    }
    
    if (currentStep < totalSteps) {
        currentStep++;
        updateStepDisplay();
    }
}

function previousStep() {
    if (currentStep > 1) {
        currentStep--;
        updateStepDisplay();
    }
}

function updateStepDisplay() {
    // Update step indicators
    document.querySelectorAll('.step').forEach(step => {
        const stepNum = parseInt(step.dataset.step);
        if (stepNum === currentStep) {
            step.classList.add('active');
        } else if (stepNum < currentStep) {
            step.classList.add('completed');
            step.classList.remove('active');
        } else {
            step.classList.remove('active', 'completed');
        }
    });
    
    // Update form steps
    document.querySelectorAll('.form-step').forEach(step => {
        const stepNum = parseInt(step.dataset.step);
        step.classList.toggle('active', stepNum === currentStep);
    });
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function validateCurrentStep() {
    const currentStepElement = document.querySelector(`.form-step[data-step="${currentStep}"]`);
    const inputs = currentStepElement.querySelectorAll('input[required], textarea[required], select[required]');
    
    let isValid = true;
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('error');
            isValid = false;
        } else {
            // Validazione specifica per containerName
            if (input.id === 'containerName') {
                if (!/^[a-z0-9\-\.]+$/.test(input.value.trim())) {
                    input.classList.add('error');
                    isValid = false;
                    showToast('Container name can only contain lowercase letters, numbers, hyphens, and dots', 'error');
                } else {
                    input.classList.remove('error');
                }
            } else {
                input.classList.remove('error');
            }
        }
    });
    
    if (!isValid && currentStep === 1) {
        showToast('Please fill in all required fields with valid values', 'error');
    }
    
    return isValid;
}

// Category handling
function handleCategoryChange() {
    const select = document.getElementById('categorySelect');
    const newInput = document.getElementById('categoryNew');
    
    if (select.value === '__new__') {
        newInput.style.display = 'block';
        newInput.required = true;
        select.style.display = 'none';
    } else {
        newInput.value = select.value;
    }
}

// Validate Docker image
async function validateImage() {
    const imageInput = document.getElementById('imageName');
    const imageName = imageInput.value.trim();
    const validationDiv = document.getElementById('imageValidation');
    
    if (!imageName) {
        showToast('Please enter an image name', 'warning');
        return;
    }
    
    validationDiv.innerHTML = '<div class="validation-loading">🔄 Checking image...</div>';
    showLoader('Validating Docker image...');
    
    try {
        const response = await fetch('/api/validate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageName })
        });
        
        const data = await response.json();
        
        if (data.exists) {
            validationDiv.innerHTML = `
                <div class="validation-success">
                    ✓ Image found!
                    <div class="image-details">
                        <strong>ID:</strong> ${data.id}<br>
                        <strong>Size:</strong> ${data.size}<br>
                        <strong>Created:</strong> ${data.created}
                    </div>
                </div>
            `;
            showToast('Image validated successfully!', 'success');
            
            // Auto-suggest container name
            const containerNameInput = document.getElementById('containerName');
            if (!containerNameInput.value) {
                const suggestedName = imageName.split(':')[0].split('/').pop();
                containerNameInput.value = suggestedName;
            }
        } else {
            validationDiv.innerHTML = `
                <div class="validation-error">
                    ✗ ${data.error || 'Image not found'}
                </div>
            `;
            showToast('Image not found or unavailable', 'error');
        }
    } catch (e) {
        validationDiv.innerHTML = `
            <div class="validation-error">
                ✗ Error: ${e.message}
            </div>
        `;
        showToast('Failed to validate image', 'error');
    } finally {
        hideLoader();
    }
}

// Auto-detect shell
async function detectShell() {
    const imageInput = document.getElementById('imageName');
    const imageName = imageInput.value.trim();
    
    if (!imageName) {
        showToast('Please enter an image name first', 'warning');
        return;
    }
    
    showLoader('Detecting available shell...');
    
    try {
        const response = await fetch('/api/detect-shell', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageName })
        });
        
        const data = await response.json();
        document.getElementById('shell').value = data.shell;
        showToast(`Detected shell: ${data.shell}`, 'success');
    } catch (e) {
        showToast('Failed to detect shell, using default', 'warning');
    } finally {
        hideLoader();
    }
}

// Preview configuration
function previewConfig() {
    if (!validateCurrentStep()) {
        return;
    }
    
    const formData = getFormData();
    const config = buildConfigObject(formData);
    
    // Format as YAML (simple representation)
    const yamlText = formatAsYAML(config);
    
    document.getElementById('previewContent').textContent = yamlText;
    document.getElementById('previewPanel').style.display = 'block';
    
    // Scroll to preview
    document.getElementById('previewPanel').scrollIntoView({ behavior: 'smooth' });
}

function closePreview() {
    document.getElementById('previewPanel').style.display = 'none';
}

function getFormData() {
    const data = {
        name: document.getElementById('containerName').value.trim(),
        image: document.getElementById('imageName').value.trim(),
        description: document.getElementById('description').value.trim(),
        category: document.getElementById('categoryNew').value.trim() || 
                  document.getElementById('categorySelect').value,
        shell: document.getElementById('shell').value,
        keep_alive_cmd: document.getElementById('keepAliveCmd').value.trim(),
        ports: document.getElementById('ports').value.trim(),
        environment: document.getElementById('environment').value.trim(),
        motd: document.getElementById('motd').value.trim()
    };
    
    // Parse ports
    if (data.ports) {
        data.ports = data.ports.split('\n')
            .map(p => p.trim())
            .filter(p => p && p.includes(':'));
    } else {
        data.ports = [];
    }
    
    return data;
}

function buildConfigObject(data) {
    const config = {
        [data.name]: {
            image: data.image,
            category: data.category,
            description: data.description,
            keep_alive_cmd: data.keep_alive_cmd,
            shell: data.shell,
            ports: data.ports
        }
    };
    
    if (data.environment) {
        config[data.name].environment = {};
        data.environment.split('\n').forEach(line => {
            if (line.includes('=')) {
                const [key, value] = line.split('=', 2);
                config[data.name].environment[key.trim()] = value.trim();
            }
        });
    }
    
    if (data.motd) {
        config[data.name].motd = data.motd;
    }
    
    return config;
}

function formatAsYAML(obj) {
    let yaml = 'images:\n';
    
    for (const [name, data] of Object.entries(obj)) {
        yaml += `  ${name}:\n`;
        yaml += `    image: ${data.image}\n`;
        yaml += `    category: ${data.category}\n`;
        yaml += `    description: ${data.description}\n`;
        yaml += `    keep_alive_cmd: ${data.keep_alive_cmd}\n`;
        yaml += `    shell: ${data.shell}\n`;
        
        if (data.ports && data.ports.length > 0) {
            yaml += `    ports:\n`;
            data.ports.forEach(port => {
                yaml += `      - ${port}\n`;
            });
        }
        
        if (data.environment && Object.keys(data.environment).length > 0) {
            yaml += `    environment:\n`;
            for (const [key, value] of Object.entries(data.environment)) {
                yaml += `      ${key}: ${value}\n`;
            }
        }
        
        if (data.motd) {
            yaml += `    motd: |\n`;
            data.motd.split('\n').forEach(line => {
                yaml += `      ${line}\n`;
            });
        }
    }
    
    return yaml;
}

// Form submission
document.getElementById('addContainerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // VALIDA TUTTI GLI STEP invece di solo quello corrente
    if (!validateAllSteps()) {
        return;
    }
    
    const confirmed = await showConfirmModal(
        'Add Container Configuration',
        'Are you sure you want to add this container configuration? The web dashboard will need to be restarted to load the new container.',
        'success'
    );
    
    if (!confirmed) return;
    
    const formData = getFormData();
    
    showLoader('Adding container configuration...');
    
    try {
        const response = await fetch('/api/add-container', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`✓ Container '${data.name}' added successfully!`, 'success');
            
            // Show success message and redirect
            setTimeout(async () => {
                const goToDashboard = await showConfirmModal(
                    'Configuration Added!',
                    'The container configuration has been added to config.yml. Would you like to go to the dashboard now?',
                    'success'
                );
                
                if (goToDashboard) {
                    window.location.href = '/';
                } else {
                    // Reset form
                    document.getElementById('addContainerForm').reset();
                    currentStep = 1;
                    updateStepDisplay();
                    document.getElementById('imageValidation').innerHTML = '';
                }
            }, 1500);
        } else {
            showToast(`Error: ${data.detail || 'Failed to add container'}`, 'error');
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    } finally {
        hideLoader();
    }
});

function validateAllSteps() {
    let isValid = true;
    const errors = [];
    
    // Step 1
    const imageName = document.getElementById('imageName').value.trim();
    const containerName = document.getElementById('containerName').value.trim();
    const description = document.getElementById('description').value.trim();
    
    if (!imageName) errors.push('Docker Image is required');
    if (!containerName) errors.push('Container Name is required');
    if (!description) errors.push('Description is required');
    
    // MODIFICA QUESTA RIGA - aggiungi \. al pattern
    if (!/^[a-z0-9\-\.]+$/.test(containerName)) {
        errors.push('Container name can only contain lowercase letters, numbers, hyphens, and dots');
    }
    
    // Step 2
    const category = document.getElementById('categoryNew').value.trim() || 
                     document.getElementById('categorySelect').value;
    if (!category) errors.push('Category is required');
    
    // Step 3
    const shell = document.getElementById('shell').value;
    if (!shell) errors.push('Shell is required');
    
    if (errors.length > 0) {
        errors.forEach(error => showToast(error, 'error'));
        isValid = false;
        
        // Vai al primo step con errori
        if (!imageName || !containerName || !description) {
            currentStep = 1;
        } else if (!category) {
            currentStep = 2;
        } else {
            currentStep = 3;
        }
        updateStepDisplay();
    }
    
    return isValid;
}

// Initialize
updateStepDisplay();