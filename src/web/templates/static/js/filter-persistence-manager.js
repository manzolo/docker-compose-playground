// =========================================================
// FILTER PERSISTENCE MANAGER - Save/restore filter state
// =========================================================

const FilterPersistenceManager = {
    /**
     * Save current filter state to session storage
     */
    saveFilterState() {
        const filterState = {
            searchTerm: DOM.get('filter')?.value || '',
            selectedCategory: DOM.get('category-filter')?.value || '',
            activeStatusFilter: FilterManager.activeStatusFilter || 'all'
        };
        sessionStorage.setItem('filterState', JSON.stringify(filterState));
    },

    /**
     * Restore filter state from session storage
     */
    restoreFilterState() {
        const savedState = sessionStorage.getItem('filterState');
        if (savedState) {
            try {
                const filterState = JSON.parse(savedState);

                const filterInput = DOM.get('filter');
                if (filterInput && filterState.searchTerm) {
                    filterInput.value = filterState.searchTerm;
                }

                const categoryFilter = DOM.get('category-filter');
                if (categoryFilter && filterState.selectedCategory) {
                    categoryFilter.value = filterState.selectedCategory;
                }

                if (filterState.activeStatusFilter) {
                    FilterManager.activeStatusFilter = filterState.activeStatusFilter;
                    DOM.queryAll('.filter-btn').forEach(btn => {
                        DOM.toggleClass(
                            btn,
                            'active',
                            btn.getAttribute('data-filter') === filterState.activeStatusFilter
                        );
                    });
                }

                FilterManager.applyFilters();

                if (filterState.searchTerm) {
                    setTimeout(() => {
                        const imageGrid = DOM.query('.image-grid');
                        if (imageGrid) {
                            imageGrid.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    }, 100);
                }

                sessionStorage.removeItem('filterState');
            } catch (error) {
                console.error('Error restoring filter state:', error);
            }
        }
    }
};

window.FilterPersistenceManager = FilterPersistenceManager;