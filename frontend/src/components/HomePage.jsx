import { useState, useEffect, useRef, useMemo } from 'react';
import { useQueryClient, useQuery } from '@tanstack/react-query';
import { ArrowPathIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

import JobList from './JobList';
import FilterPanel from './FilterPanel';

const HomePage = () => {
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [filters, setFilters] = useState({
        jobType: [],
        location: '',
        experience: '',
        search: '',
        skills: [],
        salaryRange: { min: '', max: '' }
    });

    const queryClient = useQueryClient();
    const urlUpdateTimeoutRef = useRef(null);

    // Fetch all jobs for client-side filtering
    const { data: response, isLoading, error } = useQuery({
        queryKey: ['jobs'],
        queryFn: async () => {
            const response = await axios.get('http://localhost:8000/api/jobs/');
            return response.data;
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
        refetchOnWindowFocus: false,
    });

    // Advanced filtering logic with performance optimization
    const filteredJobs = useMemo(() => {
        if (!response?.results || response.results.length === 0) return [];

        let jobs = [...response.results];

        // Text-based search with intelligent matching
        if (filters.search && filters.search.trim()) {
            const searchTerms = filters.search.toLowerCase().trim().split(/\s+/);

            jobs = jobs.filter(job => {
                const searchableContent = [
                    job.role || '',
                    job.company_name || '',
                    job.location || '',
                    job.short_description || '',
                    job.description || '',
                    ...(job.skills_required || [])
                ].join(' ').toLowerCase();

                // All search terms must be found
                return searchTerms.every(term =>
                    searchableContent.includes(term) ||
                    // Fuzzy matching for typos
                    searchableContent.split(' ').some(word =>
                        word.startsWith(term) ||
                        (term.length > 3 && word.includes(term.slice(0, -1)))
                    )
                );
            });

            // Sort by relevance when searching
            jobs.sort((a, b) => {
                let scoreA = 0, scoreB = 0;

                searchTerms.forEach(term => {
                    // Title match (highest priority)
                    if ((a.role || '').toLowerCase().includes(term)) scoreA += 10;
                    if ((b.role || '').toLowerCase().includes(term)) scoreB += 10;

                    // Company match
                    if ((a.company_name || '').toLowerCase().includes(term)) scoreA += 5;
                    if ((b.company_name || '').toLowerCase().includes(term)) scoreB += 5;

                    // Skills match
                    if (a.skills_required?.some(skill => skill.toLowerCase().includes(term))) scoreA += 3;
                    if (b.skills_required?.some(skill => skill.toLowerCase().includes(term))) scoreB += 3;

                    // Description match
                    if ((a.short_description || '').toLowerCase().includes(term)) scoreA += 1;
                    if ((b.short_description || '').toLowerCase().includes(term)) scoreB += 1;
                });

                return scoreB - scoreA;
            });
        }

        // Job type filtering
        if (filters.jobType && filters.jobType.length > 0) {
            jobs = jobs.filter(job => filters.jobType.includes(job.job_type));
        }

        // Location filtering with flexible matching
        if (filters.location && filters.location.trim()) {
            const locationTerm = filters.location.toLowerCase().trim();
            jobs = jobs.filter(job => {
                const jobLocation = (job.location || '').toLowerCase();
                return jobLocation.includes(locationTerm) ||
                    locationTerm.includes(jobLocation) ||
                    // Handle remote work
                    (locationTerm.includes('remote') && jobLocation.includes('remote'));
            });
        }

        // Experience level filtering
        if (filters.experience && filters.experience.trim()) {
            const expTerm = filters.experience.toLowerCase().trim();
            jobs = jobs.filter(job => {
                const jobExp = (job.experience_required || '').toLowerCase();

                // Handle specific cases
                if (expTerm.includes('fresh') || expTerm === '0') {
                    return jobExp.includes('0') || jobExp.includes('fresh') ||
                        jobExp.includes('entry') || jobExp.includes('junior');
                }

                // Extract years
                const expYears = expTerm.match(/(\d+)/);
                const jobYears = jobExp.match(/(\d+)/);

                if (expYears && jobYears) {
                    const targetYears = parseInt(expYears[1]);
                    const requiredYears = parseInt(jobYears[1]);
                    return Math.abs(targetYears - requiredYears) <= 1;
                }

                return jobExp.includes(expTerm);
            });
        }

        // Skills filtering with intelligent matching
        if (filters.skills && filters.skills.length > 0) {
            jobs = jobs.filter(job => {
                if (!job.skills_required || job.skills_required.length === 0) return false;

                const jobSkills = job.skills_required.map(skill => skill.toLowerCase());

                return filters.skills.some(filterSkill => {
                    const filterSkillLower = filterSkill.toLowerCase();
                    return jobSkills.some(jobSkill =>
                        jobSkill.includes(filterSkillLower) ||
                        filterSkillLower.includes(jobSkill) ||
                        // Handle similar technologies
                        (filterSkillLower === 'javascript' && jobSkill === 'js') ||
                        (filterSkillLower === 'js' && jobSkill === 'javascript') ||
                        (filterSkillLower === 'typescript' && jobSkill === 'ts') ||
                        (filterSkillLower === 'ts' && jobSkill === 'typescript')
                    );
                });
            });
        }

        // Salary range filtering
        if (filters.salaryRange && (filters.salaryRange.min || filters.salaryRange.max)) {
            jobs = jobs.filter(job => {
                if (!job.compensation) return false;

                // Extract numeric values from various salary formats
                const salaryMatch = job.compensation.match(/[\d,]+/g);
                if (!salaryMatch) return false;

                const salary = parseInt(salaryMatch[0].replace(/,/g, ''));

                if (filters.salaryRange.min && salary < parseInt(filters.salaryRange.min)) return false;
                if (filters.salaryRange.max && salary > parseInt(filters.salaryRange.max)) return false;

                return true;
            });
        }

        // Default sort by date if no search
        if (!filters.search || !filters.search.trim()) {
            jobs.sort((a, b) => new Date(b.posted_date || 0) - new Date(a.posted_date || 0));
        }

        return jobs;
    }, [response?.results, filters]);

    const handleRefreshJobs = async () => {
        setIsRefreshing(true);
        try {
            await axios.post('http://localhost:8000/api/jobs/refresh/');
            await queryClient.invalidateQueries({ queryKey: ['jobs'] });
        } catch (error) {
            console.error('Error refreshing jobs:', error);
        } finally {
            setIsRefreshing(false);
        }
    };

    const handleFilterChange = (newFilters) => {
        setFilters(newFilters);

        // Debounce URL updates to prevent constant changes
        if (urlUpdateTimeoutRef.current) {
            clearTimeout(urlUpdateTimeoutRef.current);
        }

        urlUpdateTimeoutRef.current = setTimeout(() => {
            updateURL(newFilters);
        }, 300);
    };

    const updateURL = (filtersToUpdate) => {
        // Update URL with filters for better UX
        const params = new URLSearchParams();
        if (filtersToUpdate.jobType.length > 0) {
            params.append('job_type', filtersToUpdate.jobType.join(','));
        }
        if (filtersToUpdate.location) {
            params.append('location', filtersToUpdate.location);
        }
        if (filtersToUpdate.experience) {
            params.append('experience', filtersToUpdate.experience);
        }
        if (filtersToUpdate.search) {
            params.append('search', filtersToUpdate.search);
        }
        if (filtersToUpdate.skills.length > 0) {
            params.append('skills', filtersToUpdate.skills.join(','));
        }
        if (filtersToUpdate.salaryRange.min || filtersToUpdate.salaryRange.max) {
            params.append('salary_min', filtersToUpdate.salaryRange.min || '');
            params.append('salary_max', filtersToUpdate.salaryRange.max || '');
        }

        // Update URL without page reload
        const newUrl = params.toString() ? `?${params.toString()}` : window.location.pathname;
        window.history.replaceState({}, '', newUrl);
    };

    // Cleanup timeout on unmount
    useEffect(() => {
        return () => {
            if (urlUpdateTimeoutRef.current) {
                clearTimeout(urlUpdateTimeoutRef.current);
            }
        };
    }, []);

    return (
        <>
            {/* Header */}
            <header className="bg-white/30 dark:bg-gray-800/30 backdrop-blur-lg shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex justify-between items-center">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Scraplify</h1>
                        <div className="flex items-center space-x-4">
                            <button
                                onClick={handleRefreshJobs}
                                disabled={isRefreshing}
                                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                            >
                                <ArrowPathIcon className={`-ml-1 mr-2 h-5 w-5 ${isRefreshing ? 'animate-spin' : ''}`} />
                                {isRefreshing ? 'Refreshing...' : 'Refresh Jobs'}
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {isLoading ? (
                    <div className="flex items-center justify-center h-64">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
                        <span className="ml-3 text-gray-600 dark:text-gray-300">Loading jobs...</span>
                    </div>
                ) : error ? (
                    <div className="text-center py-12">
                        <div className="text-red-600 dark:text-red-400 mb-4">
                            <svg className="mx-auto h-12 w-12 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.98-.833-2.75 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                            </svg>
                            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                                Error loading jobs
                            </h3>
                            <p className="text-gray-600 dark:text-gray-400 mb-4">
                                {error.message}
                            </p>
                            <button
                                onClick={() => window.location.reload()}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                            >
                                Try Again
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                        {/* Enhanced Filters */}
                        <div className="lg:col-span-1">
                            <div className="bg-white/30 dark:bg-gray-800/30 backdrop-blur-lg rounded-xl p-6 shadow-lg border border-white/20 dark:border-gray-700/20 sticky top-8">
                                <FilterPanel
                                    filters={filters}
                                    onFilterChange={handleFilterChange}
                                    allJobs={response?.results || []}
                                />
                            </div>
                        </div>

                        {/* Job listings */}
                        <div className="lg:col-span-3">
                            <JobList
                                jobs={filteredJobs}
                                totalJobs={response?.results?.length || 0}
                                isLoading={isLoading}
                                filters={filters}
                            />
                        </div>
                    </div>
                )}
            </main>
        </>
    );
};

export default HomePage;
