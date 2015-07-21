(function(){
    /**
     * Angular service for sharing data needed for rendering and controlling the display of course instances
     * across controllers.
     */
    angular.module('app').factory('courseInstanceModel', ['$http', 'djangoUrl', 'errorModel', 'courseInstanceFilterModel', function($http, djangoUrl, errorModel, courseInstanceFilterModel){
        var self = {};
        self.dataLoading = false;
        self.dataLoaded = false;
        self.selectedCourseInstances = {};

        self.initSummaryData = function(){
            self.totalCourses= 0;
            self.totalCoursesWithCanvasSite= 0;
            self.totalCoursesWithCanvasSiteWithISite = 0;
            self.totalCoursesWithCanvasSiteWithExternal = 0;
            self.totalCoursesWithoutCanvasSite= 0;
            self.totalCoursesWithoutCanvasSiteWithISite = 0;
            self.totalCoursesWithoutCanvasSiteWithExternal = 0;
        };
        self.initSummaryData();

        self.addSelectedCourseInstance = function(courseInstanceData){
            self.selectedCourseInstances[courseInstanceData['id']] = courseInstanceData;
        };

        self.removeSelectedCourseInstance = function(courseInstanceData){
            delete self.selectedCourseInstances[courseInstanceData['id']];
        };

        self.getSelectedCourseIdsCount = function(){
            return Object.keys(self.selectedCourseInstances).length;
        };

        self.getSelectedCourses = function(){
            return Object.keys(self.selectedCourseInstances).map(function(key){
                return self.selectedCourseInstances[key];
            })
        };

        self.loadCourseInstanceSummary = function(){
            var selectedTermId = courseInstanceFilterModel.getSelectedFilterId('term');
            if (selectedTermId) {
                var url = djangoUrl.reverse('bulk_site_creation:api_course_instance_summary', [
                    selectedTermId,
                    courseInstanceFilterModel.getAccountFilterId()
                ]);
                self.dataLoading = true;
                $http.get(url).success(function (data, status, headers, config) {
                    self.dataLoading = false;
                    self.dataLoaded = true;
                    self.totalCourses = data.recordsTotal;
                    self.totalCoursesWithCanvasSite = data.recordsTotalWithCanvasSite;
                    self.totalCoursesWithCanvasSiteWithISite = data.recordsTotalWithCanvasSiteWithISite;
                    self.totalCoursesWithCanvasSiteWithExternal = data.recordsTotalWithCanvasSiteWithExternal;
                    self.totalCoursesWithoutCanvasSite = data.recordsTotalWithoutCanvasSite;
                    self.totalCoursesWithoutCanvasSiteWithISite = data.recordsTotalWithoutCanvasSiteWithISite;
                    self.totalCoursesWithoutCanvasSiteWithExternal = data.recordsTotalWithoutCanvasSiteWithExternal;
                }).error(function (data, status, headers, config) {
                    self.dataLoading = false;
                    // status == 0 indicates that the request was cancelled which means that
                    // the user navigated away from the page before an AJAX request had a chance
                    // to return with a response, ignore this error condition
                    if (status != 0) {
                        errorModel.hasError = true;
                    }
                });
            }
        };

        return self;
    }]);
})();
