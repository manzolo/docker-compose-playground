// =========================================================
// FILTER PERSISTENCE MANAGER - Save/restore filter state
// =========================================================

const FilterPersistenceManager = {
    STORAGE_KEY: 'filterState',

    /**
     * Save current filter state to local storage
     */
    saveFilterState() {
        const filterState = {
            searchTerm: DOM.get('filter')?.value || '',
            selectedCategory: DOM.get('category-filter')?.value || '',
            activeStatusFilter: FilterManager.activeStatusFilter || 'all'
        };
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(filterState));
    },

    /**
     * Restore filter state from local storage
     */
    restoreFilterState() {
        const savedState = localStorage.getItem(this.STORAGE_KEY);
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
            } catch (error) {
                console.error('Error restoring filter state:', error);
            }
        }
    },

    /**
     * Clear saved filter state
     */
    clearSavedFilterState() {
        localStorage.removeItem(this.STORAGE_KEY);
        
        // Reset UI
        const filterInput = DOM.get('filter');
        const categoryFilter = DOM.get('category-filter');
        
        if (filterInput) {
            filterInput.value = '';
        }
        
        if (categoryFilter) {
            categoryFilter.value = '';
        }
        
        FilterManager.activeStatusFilter = 'all';
        DOM.queryAll('.filter-btn').forEach(btn => {
            DOM.toggleClass(
                btn,
                'active',
                btn.getAttribute('data-filter') === 'all'
            );
        });
        
        FilterManager.applyFilters();
        //ToastManager.show('Filtri salvati cancellati', 'info');
    },

    /**
     * Get saved filter state (without restoring)
     */
    getSavedFilterState() {
        const savedState = localStorage.getItem(this.STORAGE_KEY);
        if (savedState) {
            try {
                return JSON.parse(savedState);
            } catch (error) {
                console.error('Error parsing saved filter state:', error);
                return null;
            }
        }
        return null;
    },

    /**
     * Check if there are saved filters
     */
    hasSavedFilters() {
        const savedState = this.getSavedFilterState();
        return savedState && (
            savedState.searchTerm || 
            savedState.selectedCategory || 
            (savedState.activeStatusFilter && savedState.activeStatusFilter !== 'all')
        );
    }
};

window.FilterPersistenceManager = FilterPersistenceManager;