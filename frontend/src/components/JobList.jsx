import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
    CalendarIcon,
    MapPinIcon,
    BanknotesIcon,
    BuildingOfficeIcon,
    SparklesIcon,
    FunnelIcon,
    MagnifyingGlassIcon,
    ArrowTopRightOnSquareIcon
} from '@heroicons/react/24/outline';

const JobCard = ({ job, searchTerms = [] }) => {
    const navigate = useNavigate();

    const handleViewDetails = () => {
        navigate(`/job/${job.id}`);
    };

    const handleApply = (e) => {
        e.stopPropagation(); // Prevent triggering the card click
        if (job.apply_link) {
            window.open(job.apply_link, '_blank', 'noopener,noreferrer');
        }
    };

    const highlightText = (text, terms) => {
        if (!text || !terms.length) return text;

        let highlightedText = text;
        terms.forEach(term => {
            const regex = new RegExp(`(${term})`, 'gi');
            highlightedText = highlightedText.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800 rounded px-1">$1</mark>');
        });

        return <span dangerouslySetInnerHTML={{ __html: highlightedText }} />;
    };

    const formatSalary = (compensation) => {
        if (!compensation) return null;
        // Clean up salary format
        return compensation.replace(/[^\d\-,\s]/g, '').trim();
    };

    return (
        <div
            onClick={handleViewDetails}
            className="bg-white/40 dark:bg-gray-800/40 backdrop-blur-lg rounded-xl p-6 border border-white/30 dark:border-gray-700/30 hover:bg-white/50 dark:hover:bg-gray-800/50 transition-all duration-300 cursor-pointer group shadow-lg hover:shadow-xl transform hover:-translate-y-1"
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
                <div className="flex-1 min-w-0">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors mb-2 line-clamp-2">
                        {highlightText(job.role, searchTerms)}
                        {searchTerms.length > 0 && (
                            <SparklesIcon className="inline h-4 w-4 ml-2 text-yellow-500" />
                        )}
                    </h3>
                    <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-300 mb-2">
                        <div className="flex items-center space-x-1">
                            <BuildingOfficeIcon className="h-4 w-4 flex-shrink-0" />
                            <span className="truncate">{highlightText(job.company_name || job.company, searchTerms)}</span>
                        </div>
                        {job.location && (
                            <div className="flex items-center space-x-1">
                                <MapPinIcon className="h-4 w-4 flex-shrink-0" />
                                <span className="truncate">{highlightText(job.location, searchTerms)}</span>
                            </div>
                        )}
                    </div>
                    {job.compensation && (
                        <div className="flex items-center space-x-1 text-sm font-medium text-green-600 dark:text-green-400">
                            <BanknotesIcon className="h-4 w-4 flex-shrink-0" />
                            <span>{formatSalary(job.compensation)}</span>
                        </div>
                    )}
                </div>
                <div className="flex flex-col items-end space-y-2">
                    <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center space-x-1">
                        <CalendarIcon className="h-3 w-3" />
                        <span>{new Date(job.posted_date).toLocaleDateString()}</span>
                    </div>
                    {job.job_type && (
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${job.job_type === 'FULL_TIME'
                                ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100'
                                : job.job_type === 'INTERNSHIP'
                                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100'
                                    : job.job_type === 'PART_TIME'
                                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-800 dark:text-purple-100'
                                        : 'bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100'
                            }`}>
                            {job.job_type === 'FULL_TIME' ? 'Full-time' :
                                job.job_type === 'INTERNSHIP' ? 'Internship' :
                                    job.job_type === 'PART_TIME' ? 'Part-time' :
                                        job.job_type === 'CONTRACT' ? 'Contract' :
                                            job.job_type}
                        </span>
                    )}
                </div>
            </div>

            {/* Description */}
            {(job.short_description || job.description) && (
                <div className="mb-4">
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed line-clamp-3">
                        {highlightText(
                            (job.short_description || job.description || '').substring(0, 200) +
                                (job.short_description || job.description || '').length > 200 ? '...' : '',
                            searchTerms
                        )}
                    </p>
                </div>
            )}

            {/* Skills */}
            {job.skills_required && job.skills_required.length > 0 && (
                <div className="mb-6">
                    <div className="flex flex-wrap gap-2">
                        {job.skills_required.slice(0, 6).map((skill, index) => (
                            <span
                                key={index}
                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors ${searchTerms.some(term => skill.toLowerCase().includes(term.toLowerCase()))
                                        ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-800 dark:text-indigo-200 ring-2 ring-indigo-300 dark:ring-indigo-700'
                                        : 'bg-gray-100 dark:bg-gray-700/50 text-gray-800 dark:text-gray-200'
                                    }`}
                            >
                                {highlightText(skill, searchTerms)}
                            </span>
                        ))}
                        {job.skills_required.length > 6 && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700/50 text-gray-800 dark:text-gray-200">
                                +{job.skills_required.length - 6} more
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Action Buttons */}
            <div className="flex space-x-3">
                <button
                    onClick={handleViewDetails}
                    className="flex-1 bg-indigo-600 dark:bg-indigo-500 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 dark:hover:bg-indigo-600 transition-colors font-medium text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                >
                    View Details
                </button>
                {job.apply_link && (
                    <button
                        onClick={handleApply}
                        className="flex-1 bg-green-600 dark:bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-700 dark:hover:bg-green-600 transition-colors font-medium text-sm flex items-center justify-center space-x-1 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                    >
                        <span>Apply</span>
                        <ArrowTopRightOnSquareIcon className="h-3 w-3" />
                    </button>
                )}
            </div>
        </div>
    );
};

const JobList = ({ jobs = [], totalJobs = 0, isLoading = false, filters = {} }) => {
    const searchTerms = filters.search ? filters.search.toLowerCase().split(/\s+/).filter(term => term.length > 0) : [];

    if (isLoading) {
        return (
            <div className="space-y-6">
                {[...Array(6)].map((_, index) => (
                    <div key={index} className="bg-white/20 dark:bg-gray-800/20 backdrop-blur-lg rounded-xl p-6 animate-pulse">
                        <div className="flex justify-between items-start mb-4">
                            <div className="flex-1">
                                <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded w-3/4 mb-2"></div>
                                <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/2 mb-2"></div>
                                <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/3"></div>
                            </div>
                            <div className="w-20 h-6 bg-gray-300 dark:bg-gray-600 rounded"></div>
                        </div>
                        <div className="space-y-2 mb-4">
                            <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-full"></div>
                            <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-2/3"></div>
                        </div>
                        <div className="flex flex-wrap gap-2 mb-4">
                            {[...Array(4)].map((_, i) => (
                                <div key={i} className="h-6 w-16 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
                            ))}
                        </div>
                        <div className="flex space-x-3">
                            <div className="flex-1 h-10 bg-gray-300 dark:bg-gray-600 rounded-lg"></div>
                            <div className="flex-1 h-10 bg-gray-300 dark:bg-gray-600 rounded-lg"></div>
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    if (jobs.length === 0) {
        return (
            <div className="text-center py-16">
                <div className="mx-auto w-24 h-24 mb-6">
                    <FunnelIcon className="w-full h-full text-gray-400" />
                </div>
                <h3 className="text-xl font-medium text-gray-900 dark:text-white mb-2">
                    No jobs found
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
                    We couldn't find any jobs matching your current filters. Try adjusting your search criteria to discover more opportunities.
                </p>
                <div className="text-sm text-gray-500 dark:text-gray-500 space-y-1">
                    <p>Total jobs available: <span className="font-medium">{totalJobs}</span></p>
                    {filters.search && <p>Search: "<span className="font-medium">{filters.search}</span>"</p>}
                    {filters.location && <p>Location: <span className="font-medium">{filters.location}</span></p>}
                    {filters.skills && filters.skills.length > 0 && (
                        <p>Skills: <span className="font-medium">{filters.skills.join(', ')}</span></p>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Results Summary */}
            <div className="flex items-center justify-between bg-white/30 dark:bg-gray-800/30 backdrop-blur-lg rounded-lg px-6 py-4 border border-white/20 dark:border-gray-700/20">
                <div className="flex items-center space-x-3">
                    <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                        Showing <span className="font-semibold text-gray-900 dark:text-white">{jobs.length}</span> of{' '}
                        <span className="font-semibold text-gray-900 dark:text-white">{totalJobs}</span> jobs
                    </div>
                </div>

                <div className="flex items-center space-x-4">
                    {filters.search && (
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                            for "<span className="font-medium text-gray-900 dark:text-white">{filters.search}</span>"
                        </div>
                    )}
                    {searchTerms.length > 0 && (
                        <div className="text-xs text-indigo-600 dark:text-indigo-400 flex items-center space-x-1">
                            <SparklesIcon className="h-3 w-3" />
                            <span>Sorted by relevance</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Job Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {jobs.map((job) => (
                    <JobCard
                        key={job.id}
                        job={job}
                        searchTerms={searchTerms}
                    />
                ))}
            </div>

            {/* Load More Indicator */}
            {jobs.length > 0 && jobs.length < totalJobs && (
                <div className="text-center py-8">
                    <div className="inline-flex items-center px-4 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm text-gray-600 dark:text-gray-400">
                        <span>Showing {jobs.length} of {totalJobs} total jobs</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default JobList;
