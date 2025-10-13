function showLoader(message = 'Please wait...') {
    const loader = document.getElementById('globalLoader');
    const loaderMessage = loader.querySelector('.loader-message');
    if (loader && loaderMessage) {
        loaderMessage.textContent = message;
        loader.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function hideLoader() {
    const loader = document.getElementById('globalLoader');
    if (loader) {
        loader.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Funzione per mostrare il modal di conferma
function showConfirmModal(title, message, type = 'danger') {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        if (!modal) {
            console.error('Confirm modal not found in DOM');
            resolve(false);
            return;
        }

        // Pulisci il contenuto precedente
        modal.innerHTML = '';

        // Determina icona e classe in base al tipo
        const icons = {
            danger: '⚠️',
            warning: '⚡',
            info: 'ℹ️',
            success: '✓',
            question: '❓'
        };
        const icon = icons[type] || icons.danger;
        
        const buttonClass = type === 'danger' ? 'btn-confirm-danger' : 
                           type === 'success' ? 'btn-confirm-success' : 
                           'btn-confirm-primary';

        // Crea contenuto modal
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="confirm-modal-header">
                    <h2>
                        <span class="confirm-modal-icon">${icon}</span>
                        ${title}
                    </h2>
                </div>
                <div class="confirm-modal-body">
                    <p class="confirm-modal-message">${message}</p>
                </div>
                <div class="confirm-modal-footer">
                    <button class="btn btn-confirm-cancel" id="confirmModalCancel">
                        <span class="btn-icon-confirm">✕</span>
                        Cancel
                    </button>
                    <button class="btn ${buttonClass}" id="confirmModalConfirm">
                        <span class="btn-icon-confirm">✓</span>
                        Confirm
                    </button>
                </div>
            </div>
        `;

        const confirmBtn = modal.querySelector('#confirmModalConfirm');
        const cancelBtn = modal.querySelector('#confirmModalCancel');
        const overlay = modal.querySelector('.modal-overlay');

        modal.classList.add('modal-open');
        document.body.style.overflow = 'hidden';

        // Focus sul pulsante di conferma dopo l'animazione
        setTimeout(() => confirmBtn.focus(), 100);

        const cleanup = () => {
            modal.classList.remove('modal-open');
            document.body.style.overflow = '';
            confirmBtn.removeEventListener('click', onConfirm);
            cancelBtn.removeEventListener('click', onCancel);
            overlay.removeEventListener('click', onCancel);
            document.removeEventListener('keydown', onKeyDown);
        };

        const onConfirm = () => {
            cleanup();
            resolve(true);
        };

        const onCancel = () => {
            cleanup();
            resolve(false);
        };

        const onKeyDown = (e) => {
            if (e.key === 'Escape') {
                onCancel();
            } else if (e.key === 'Enter' && e.ctrlKey) {
                onConfirm();
            }
        };

        confirmBtn.addEventListener('click', onConfirm);
        cancelBtn.addEventListener('click', onCancel);
        overlay.addEventListener('click', onCancel);
        document.addEventListener('keydown', onKeyDown);
    });
}

// Funzione per input di categoria
function showInputModal(title, message, placeholder = 'Enter value...', defaultValue = '') {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        if (!modal) {
            console.error('Confirm modal not found in DOM');
            resolve(null);
            return;
        }

        // Pulisci il contenuto precedente
        modal.innerHTML = '';

        // Crea contenuto modal
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="confirm-modal-header">
                    <h2>
                        <span class="confirm-modal-icon">📝</span>
                        ${title}
                    </h2>
                </div>
                <div class="confirm-modal-body">
                    <p class="confirm-modal-message">${message}</p>
                    <label class="input-label">
                        Category Name
                        <input 
                            type="text" 
                            id="confirmModalInput" 
                            class="confirm-input" 
                            placeholder="${placeholder}"
                            value="${defaultValue}"
                            autocomplete="off"
                        />
                        <span class="input-hint">💡 Examples: linux, database, programming</span>
                    </label>
                </div>
                <div class="confirm-modal-footer">
                    <button class="btn btn-confirm-cancel" id="confirmModalCancel">
                        <span class="btn-icon-confirm">✕</span>
                        Cancel
                    </button>
                    <button class="btn btn-confirm-primary" id="confirmModalConfirm">
                        <span class="btn-icon-confirm">✓</span>
                        Confirm
                    </button>
                </div>
            </div>
        `;

        const input = modal.querySelector('#confirmModalInput');
        const confirmBtn = modal.querySelector('#confirmModalConfirm');
        const cancelBtn = modal.querySelector('#confirmModalCancel');
        const overlay = modal.querySelector('.modal-overlay');

        modal.classList.add('modal-open');
        document.body.style.overflow = 'hidden';

        // Focus sull'input dopo l'animazione
        setTimeout(() => {
            input.focus();
            input.select();
        }, 100);

        const cleanup = () => {
            modal.classList.remove('modal-open');
            document.body.style.overflow = '';
            confirmBtn.removeEventListener('click', onConfirm);
            cancelBtn.removeEventListener('click', onCancel);
            overlay.removeEventListener('click', onCancel);
            input.removeEventListener('keydown', onInputKeyDown);
        };

        const onConfirm = () => {
            const value = input.value.trim();
            cleanup();
            resolve(value || null);
        };

        const onCancel = () => {
            cleanup();
            resolve(null);
        };

        const onInputKeyDown = (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                onConfirm();
            } else if (e.key === 'Escape') {
                onCancel();
            }
        };

        confirmBtn.addEventListener('click', onConfirm);
        cancelBtn.addEventListener('click', onCancel);
        overlay.addEventListener('click', onCancel);
        input.addEventListener('keydown', onInputKeyDown);
    });
}