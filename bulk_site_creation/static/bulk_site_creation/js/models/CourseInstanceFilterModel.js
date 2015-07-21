(function(){
    /**
     * Angular service for sharing data needed for rendering and controlling course instance filters
     * across controllers.
     */
    angular.module('app').factory('courseInstanceFilterModel', ['$http', 'djangoUrl', 'errorModel', function($http, djangoUrl, errorModel){
        var defaults = {
            DEFAULT_FILTER_ID: 'default',
            DEFAULT_FILTER_TEXT: {
                school: 'Please select a school...',
                term: 'Please select an academic term...',
                department: 'All Departments',
                course_group: 'All Course Groups'
            },
            ALWAYS_ADD_DEFAULT_FILTER: {
                school: false,
                term: false,
                department: true,
                course_group: true
            }
        };
        var filters = window.globals.bulk_site_creation_filters || {
            school: '',
            term: '',
            department: '',
            course_group: ''
        };
        var loading = {
            school: false,
            term: false,
            department: false,
            course_group: false
        };
        var disabled = {
            department: false,
            course_group: false
        };
        var filterOptions = {
            school: window.globals.bulk_site_creation_schools || [],
            term: window.globals.bulk_site_creation_terms || [],
            departments: window.globals.bulk_site_creation_departments || [],
            course_groups: window.globals.bulk_site_creation_course_groups || []
        };

        function initFilterOptions(options) {
            options = options || {
                school: window.globals.bulk_site_creation_schools || [],
                term: window.globals.bulk_site_creation_terms || [],
                department: window.globals.bulk_site_creation_departments || [],
                course_group: window.globals.bulk_site_creation_course_groups || []
            };
            for (var filterType in options) {
                filterOptions[filterType] = options[filterType];
                var filterOptionCount = filterOptions[filterType].length;
                if (filterOptionCount) {
                    if (filterOptionCount > 1 || defaults.ALWAYS_ADD_DEFAULT_FILTER[filterType]) {
                        filterOptions[filterType].unshift({
                            id: defaults.DEFAULT_FILTER_ID,
                            name: defaults.DEFAULT_FILTER_TEXT[filterType]
                        });
                    }
                    filters[filterType] = filters[filterType] || filterOptions[filterType][0].id;
                }
            }
        }

        function getUrl(filterType) {
            var pluralizedFilterType = filterType + 's';
            return djangoUrl.reverse('bulk_site_creation:api_' + pluralizedFilterType, [filters.school]);
        }

        function loadFilterOptions(filterType) {
            filters[filterType] = '';
            filterOptions[filterType] = [];
            loading[filterType] = true;
            var url = getUrl(filterType);
            $http.get(url).success(function(data, status, headers, config){
                loading[filterType] = false;
                var options = {};
                options[filterType] = data;
                initFilterOptions(options);
            }).error(function(data, status, headers, config){
                loading[filterType] = false;
                errorModel.hasError = true;
            });
        }

        function isFilterSelectable(filterType) {
            return filterOptions[filterType].length > 1;
        }

        function getSelectedFilters() {
            var selectedFilters = {};
            for (var filterType in filters) {
                if (filters[filterType] != defaults.DEFAULT_FILTER_ID) {
                    selectedFilters[filterType] = filters[filterType];
                }
            }
            return selectedFilters;
        }

        function getSelectedFilterId(filterType) {
            var id = '';
            if (filters[filterType] != defaults.DEFAULT_FILTER_ID) {
                id = filters[filterType];
            }
            return id;
        }

        function getSelectedFilterName(filterType) {
            var name = '';
            var selectedFilterId = getSelectedFilterId(filterType);
            if (selectedFilterId) {
                var options = filterOptions[filterType];
                for (var i = 0; i < options.length; i++) {
                    var option = options[i];
                    if (selectedFilterId == option.id) {
                        name = option.name;
                        break;
                    }
                }
            }
            return name;
        }

        function getAccountFilterId(){
            return getSelectedFilterId('course_group') ||
                getSelectedFilterId('department') ||
                getSelectedFilterId('school');
        }

        return {
            defaults: defaults,
            filters: filters,
            loading: loading,
            disabled: disabled,
            filterOptions: filterOptions,
            initFilterOptions: initFilterOptions,
            loadFilterOptions: loadFilterOptions,
            isFilterSelectable: isFilterSelectable,
            getSelectedFilters: getSelectedFilters,
            getSelectedFilterId: getSelectedFilterId,
            getSelectedFilterName: getSelectedFilterName,
            getAccountFilterId: getAccountFilterId
        };
    }]);
})();
