// =========================================================
// FILTER MANAGER - Dashboard filtering and search
// =========================================================

const FilterManager = {
    activeStatusFilter: 'all',

    /**
     * Initialize filters
     */
    init() {
        const filterInput = DOM.get('filter');
        const categoryFilter = DOM.get('category-filter');

        if (filterInput) {
            DOM.on(filterInput, 'input', () => this.applyFilters());
        }
        if (categoryFilter) {
            DOM.on(categoryFilter, 'change', () => this.applyFilters());
        }

        this.applyFilters();
    },

    /**
     * Apply all active filters
     */
    applyFilters() {
        const searchTerm = DOM.get('filter')?.value.toLowerCase() || '';
        const selectedCategory = DOM.get('category-filter')?.value.toLowerCase() || '';

        // Filter individual containers - cerca .container-card
        DOM.queryAll('.container-card').forEach(card => {
            const matches = this.cardMatchesFilters(card, searchTerm, selectedCategory);
            card.style.display = matches ? '' : 'none';
        });

        // Filter groups
        DOM.queryAll('.group-card').forEach(groupCard => {
            const groupName = groupCard.getAttribute('data-group').toLowerCase();
            const searchData = groupCard.getAttribute('data-search').toLowerCase();

            const matchesSearch = !searchTerm ||
                groupName.includes(searchTerm) ||
                searchData.includes(searchTerm);

            const matchesCategory = !selectedCategory ||
                groupCard.querySelector('.badge')?.className.includes('badge-' + selectedCategory);

            let matchesStatus = true;
            if (this.activeStatusFilter !== 'all') {
                const containerTags = groupCard.querySelectorAll('.container-tag');
                const hasMatchingContainer = Array.from(containerTags).some(tag => {
                    const containerName = tag.getAttribute('data-container');
                    const containerCard = DOM.query(`.container-card[data-name="${containerName}"]`);

                    if (!containerCard) return false;

                    // Cerca status nel .status-dot
                    const statusDot = containerCard.querySelector('.status-dot');
                    const isRunning = statusDot && statusDot.classList.contains('running');
                    const status = isRunning ? 'running' : 'stopped';
                    return status === this.activeStatusFilter;
                });

                matchesStatus = hasMatchingContainer;
            }

            groupCard.style.display = (matchesSearch && matchesCategory && matchesStatus) ? '' : 'none';
        });

        this.updateCounts();
    },

    /**
     * Check if card matches all active filters
     */
    cardMatchesFilters(card, searchTerm, selectedCategory) {
        const name = card.getAttribute('data-name').toLowerCase();
        const category = card.getAttribute('data-category').toLowerCase();
        
        // Cerca lo status nel .status-dot (running/stopped class)
        const statusDot = card.querySelector('.status-dot');
        const isRunning = statusDot && statusDot.classList.contains('running');
        const status = isRunning ? 'running' : 'stopped';

        const matchesSearch = searchTerm ?
            (name.includes(searchTerm) || category.includes(searchTerm)) : true;
        const matchesCategory = selectedCategory ?
            category === selectedCategory : true;
        const matchesStatus = this.activeStatusFilter === 'all' ?
            true : status === this.activeStatusFilter;

        return matchesSearch && matchesCategory && matchesStatus;
    },

    /**
     * Update filter badge counts
     */
    updateCounts() {
        // Count all container cards (including group containers)
        const allCards = DOM.queryAll('.container-card');

        let totalCount = allCards.length;
        let runningCount = 0;
        let stoppedCount = 0;

        allCards.forEach(card => {
            const statusDot = card.querySelector('.status-dot');
            const isRunning = statusDot && statusDot.classList.contains('running');
            if (isRunning) {
                runningCount++;
            } else {
                stoppedCount++;
            }
        });

        let visibleCount = 0;
        allCards.forEach(card => {
            if (card.style.display !== 'none') {
                visibleCount++;
            }
        });

        const allElement = DOM.get('count-all');
        const runningElement = DOM.get('count-running');
        const stoppedElement = DOM.get('count-stopped');

        if (allElement) allElement.textContent = totalCount;
        if (runningElement) runningElement.textContent = runningCount;
        if (stoppedElement) stoppedElement.textContent = stoppedCount;

        const searchCount = DOM.get('search-count');
        if (searchCount) {
            searchCount.textContent = `${visibleCount} of ${totalCount} containers`;
        }
    },

    /**
     * Filter by status
     */
    filterByStatus(status) {
        this.activeStatusFilter = status;

        DOM.queryAll('.filter-btn').forEach(btn => {
            DOM.toggleClass(btn, 'active', btn.getAttribute('data-filter') === status);
        });

        this.applyFilters();
    },

    /**
     * Clear search input
     */
    clearSearch() {
        const filterInput = DOM.get('filter');
        if (filterInput) {
            filterInput.value = '';
            filterInput.focus();
            this.applyFilters();
            FilterPersistenceManager.clearSavedFilterState();
            //ToastManager.show('📄 Search cleared', 'info');
        }
    },

    /**
     * Quick search container
     */
    quickSearchContainer(containerName) {
        const filterInput = DOM.get('filter');
        if (filterInput) {
            filterInput.value = containerName;
            filterInput.focus();
            this.applyFilters();
            FilterPersistenceManager.saveFilterState();
            this.highlightMatchingCard(containerName);
            ToastManager.show(`🔍 Filtered to: ${containerName}`, 'info');
        }
    },

    /**
     * Highlight matching card
     */
    highlightMatchingCard(containerName) {
        const containersGrid = DOM.query('.containers-grid');
        if (containersGrid) {
            containersGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        setTimeout(() => {
            const matchingCard = DOM.query(`.container-card[data-name="${containerName}"]`);
            if (matchingCard) {
                matchingCard.style.transition = 'all 0.3s ease';
                matchingCard.style.transform = 'scale(1.02)';
                matchingCard.style.boxShadow = '0 8px 30px rgba(102, 126, 234, 0.3)';

                setTimeout(() => {
                    matchingCard.style.transform = '';
                    matchingCard.style.boxShadow = '';
                }, 600);
            }
        }, 300);
    }
};

window.FilterManager = FilterManager;