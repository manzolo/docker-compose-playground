// =========================================================
// ADD CONTAINER MANAGER - Form handling for add-container page
// =========================================================

const AddContainerManager = {
    currentStep: 1,
    totalSteps: 3,

    /**
     * Initialize form
     */
    init() {
        this.updateStepDisplay();
        const form = DOM.get('addContainerForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
    },

    /**
     * Navigate to next step
     */
    nextStep() {
        if (!this.validateCurrentStep()) {
            return;
        }
        
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.updateStepDisplay();
        }
    },

    /**
     * Navigate to previous step
     */
    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateStepDisplay();
        }
    },

    /**
     * Update step display
     */
    updateStepDisplay() {
        DOM.queryAll('.step').forEach(step => {
            const stepNum = parseInt(step.dataset.step);
            if (stepNum === this.currentStep) {
                DOM.addClass(step, 'active');
                DOM.removeClass(step, 'completed');
            } else if (stepNum < this.currentStep) {
                DOM.addClass(step, 'completed');
                DOM.removeClass(step, 'active');
            } else {
                DOM.removeClass(step, 'active');
                DOM.removeClass(step, 'completed');
            }
        });
        
        DOM.queryAll('.form-step').forEach(step => {
            const stepNum = parseInt(step.dataset.step);
            if (stepNum === this.currentStep) {
                DOM.addClass(step, 'active');
            } else {
                DOM.removeClass(step, 'active');
            }
        });
        
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    /**
     * Validate current step
     */
    validateCurrentStep() {
        const currentStepElement = DOM.query(`.form-step[data-step="${this.currentStep}"]`);
        const inputs = currentStepElement.querySelectorAll('input[required], textarea[required], select[required]');
        
        let isValid = true;
        inputs.forEach(input => {
            if (!input.value.trim()) {
                DOM.addClass(input, 'error');
                isValid = false;
            } else {
                if (input.id === 'containerName') {
                    if (!/^[a-z0-9\-\.]+$/.test(input.value.trim())) {
                        DOM.addClass(input, 'error');
                        isValid = false;
                        ToastManager.show('Container name can only contain lowercase letters, numbers, hyphens, and dots', 'error');
                    } else {
                        DOM.removeClass(input, 'error');
                    }
                } else {
                    DOM.removeClass(input, 'error');
                }
            }
        });
        
        if (!isValid && this.currentStep === 1) {
            ToastManager.show('Please fill in all required fields with valid values', 'error');
        }
        
        return isValid;
    },

    /**
     * Handle category change
     */
    handleCategoryChange() {
        const select = DOM.get('categorySelect');
        const newInput = DOM.get('categoryNew');
        
        if (select.value === '__new__') {
            newInput.style.display = 'block';
            newInput.required = true;
            select.style.display = 'none';
        } else {
            newInput.value = select.value;
            newInput.style.display = 'none';
            newInput.required = false;
            select.style.display = 'block';
        }
    },

    /**
     * Validate Docker image
     */
    async validateImage() {
        const imageInput = DOM.get('imageName');
        const imageName = imageInput.value.trim();
        const validationDiv = DOM.get('imageValidation');
        
        if (!imageName) {
            ToastManager.show('Please enter an image name', 'warning');
            return;
        }
        
        validationDiv.innerHTML = '<div class="validation-loading">🔄 Checking image...</div>';
        showLoader('Validating Docker image...');
        
        try {
            const data = await ApiService.validateImage(imageName);
            
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
                ToastManager.show('Image validated successfully!', 'success');
                
                const containerNameInput = DOM.get('containerName');
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
                ToastManager.show('Image not found or unavailable', 'error');
            }
        } catch (e) {
            validationDiv.innerHTML = `
                <div class="validation-error">
                    ✗ Error: ${e.message}
                </div>
            `;
            ToastManager.show('Failed to validate image', 'error');
        } finally {
            hideLoader();
        }
    },

    /**
     * Auto-detect shell
     */
    async detectShell() {
        const imageInput = DOM.get('imageName');
        const imageName = imageInput.value.trim();
        
        if (!imageName) {
            ToastManager.show('Please enter an image name first', 'warning');
            return;
        }
        
        showLoader('Detecting available shell...');
        
        try {
            const data = await ApiService.detectShell(imageName);
            DOM.get('shell').value = data.shell;
            ToastManager.show(`Detected shell: ${data.shell}`, 'success');
        } catch (e) {
            ToastManager.show('Failed to detect shell, using default', 'warning');
        } finally {
            hideLoader();
        }
    },

    /**
     * Preview configuration
     */
    previewConfig() {
        if (!this.validateCurrentStep()) {
            return;
        }
        
        const formData = this.getFormData();
        const config = this.buildConfigObject(formData);
        const yamlText = this.formatAsYAML(config);
        
        DOM.get('previewContent').textContent = yamlText;
        DOM.get('previewPanel').style.display = 'block';
        DOM.get('previewPanel').scrollIntoView({ behavior: 'smooth' });
    },

    /**
     * Close preview
     */
    closePreview() {
        DOM.get('previewPanel').style.display = 'none';
    },

    /**
     * Get form data
     */
    getFormData() {
        const data = {
            name: DOM.get('containerName').value.trim(),
            image: DOM.get('imageName').value.trim(),
            description: DOM.get('description').value.trim(),
            category: DOM.get('categoryNew').value.trim() || DOM.get('categorySelect').value,
            shell: DOM.get('shell').value,
            keep_alive_cmd: DOM.get('keepAliveCmd').value.trim(),
            ports: DOM.get('ports').value.trim(),
            environment: DOM.get('environment').value.trim(),
            motd: DOM.get('motd').value.trim()
        };
        
        if (data.ports) {
            data.ports = data.ports.split('\n')
                .map(p => p.trim())
                .filter(p => p && p.includes(':'));
        } else {
            data.ports = [];
        }
        
        return data;
    },

    /**
     * Build config object
     */
    buildConfigObject(data) {
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
    },

    /**
     * Format as YAML
     */
    formatAsYAML(obj) {
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
    },

    /**
     * Validate all steps
     */
    validateAllSteps() {
        let isValid = true;
        const errors = [];
        
        const imageName = DOM.get('imageName').value.trim();
        const containerName = DOM.get('containerName').value.trim();
        const description = DOM.get('description').value.trim();
        
        if (!imageName) errors.push('Docker Image is required');
        if (!containerName) errors.push('Container Name is required');
        if (!description) errors.push('Description is required');
        
        if (!/^[a-z0-9\-\.]+$/.test(containerName)) {
            errors.push('Container name can only contain lowercase letters, numbers, hyphens, and dots');
        }
        
        const category = DOM.get('categoryNew').value.trim() || DOM.get('categorySelect').value;
        if (!category) errors.push('Category is required');
        
        const shell = DOM.get('shell').value;
        if (!shell) errors.push('Shell is required');
        
        if (errors.length > 0) {
            errors.forEach(error => ToastManager.show(error, 'error'));
            isValid = false;
            
            if (!imageName || !containerName || !description) {
                this.currentStep = 1;
            } else if (!category) {
                this.currentStep = 2;
            } else {
                this.currentStep = 3;
            }
            this.updateStepDisplay();
        }
        
        return isValid;
    },

    /**
     * Handle form submission
     */
    async handleSubmit(e) {
        e.preventDefault();
        
        if (!this.validateAllSteps()) {
            return;
        }
        
        const confirmed = await showConfirmModal(
            'Add Container Configuration',
            'Are you sure you want to add this container configuration? The web dashboard will need to be restarted to load the new container.',
            'success'
        );
        
        if (!confirmed) return;
        
        const formData = this.getFormData();
        showLoader('Adding container configuration...');
        
        try {
            const data = await ApiService.addContainer(formData);
            hideLoader();
            ToastManager.show(`✓ Container '${data.name}' added successfully!`, 'success');
            
            setTimeout(async () => {
                const goToDashboard = await showConfirmModal(
                    'Configuration Added!',
                    'The container configuration has been added to config.yml. Would you like to go to the dashboard now?',
                    'success'
                );
                
                if (goToDashboard) {
                    window.location.href = '/';
                } else {
                    this.resetForm();
                }
            }, 1500);
        } catch (e) {
            hideLoader();
            ToastManager.show(`Error: ${e.message}`, 'error');
        }
    },

    /**
     * Reset form to initial state
     */
    resetForm() {
        DOM.get('addContainerForm').reset();
        this.currentStep = 1;
        this.updateStepDisplay();
        DOM.get('imageValidation').innerHTML = '';
        DOM.get('categoryNew').style.display = 'none';
        DOM.get('categorySelect').style.display = 'block';
        DOM.get('categorySelect').value = '';
    }
};

window.AddContainerManager = AddContainerManager;
window.nextStep = () => AddContainerManager.nextStep();
window.previousStep = () => AddContainerManager.previousStep();
window.validateImage = () => AddContainerManager.validateImage();
window.detectShell = () => AddContainerManager.detectShell();
window.previewConfig = () => AddContainerManager.previewConfig();
window.closePreview = () => AddContainerManager.closePreview();
window.handleCategoryChange = () => AddContainerManager.handleCategoryChange();