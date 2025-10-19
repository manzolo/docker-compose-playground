// =========================================================
// ACCORDION MANAGER - Manage accordion open/close
// =========================================================

const AccordionManager = {
    /**
     * Toggle accordion open/close
     */
    toggle(header) {
        const content = header.nextElementSibling;
        const toggle = header.querySelector('.accordion-toggle');
        const isOpen = DOM.hasClass(content, 'open');

        if (isOpen) {
            // CHIUDI
            content.style.maxHeight = '0px';
            DOM.removeClass(content, 'open');
            DOM.removeClass(toggle, 'open');
        } else {
            // APRI
            DOM.addClass(content, 'open');
            DOM.addClass(toggle, 'open');
            requestAnimationFrame(() => {
                content.style.maxHeight = content.scrollHeight + 'px';
            });
        }
    },

    /**
     * Initialize accordions - set height for those with 'open' class
     */
    initializeAccordions() {
        DOM.queryAll('.accordion-section').forEach(section => {
            const header = section.querySelector('.accordion-header');
            const content = section.querySelector('.accordion-content');
            const toggle = header.querySelector('.accordion-toggle');

            // Se ha la classe 'open', imposta l'altezza iniziale
            if (content && DOM.hasClass(content, 'open')) {
                DOM.addClass(toggle, 'open');
                requestAnimationFrame(() => {
                    content.style.maxHeight = content.scrollHeight + 'px';
                });
            }

            // Registra il click handler
            if (header) {
                DOM.on(header, 'click', (e) => {
                    e.preventDefault();
                    this.toggle(header);
                });
            }
        });
    }
};

window.AccordionManager = AccordionManager;