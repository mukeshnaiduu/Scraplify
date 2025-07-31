import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
    ArrowLeftIcon,
    BuildingOfficeIcon,
    MapPinIcon,
    ClockIcon,
    CurrencyDollarIcon,
    ArrowTopRightOnSquareIcon,
    BriefcaseIcon,
    CalendarIcon,
    TagIcon
} from '@heroicons/react/24/outline';

const JobDetails = () => {
    const { id } = useParams();
    const navigate = useNavigate();

    // Fetch job details
    const { data: job, isLoading, error } = useQuery({
        queryKey: ['job', id],
        queryFn: async () => {
            const response = await axios.get(`http://localhost:8000/api/jobs/${id}/`);
            return response.data;
        },
        enabled: !!id
    });

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    };

    const formatDescription = (description) => {
        if (!description) return '';

        // Convert newlines to line breaks and preserve formatting
        return description
            .split('\n')
            .map((line, index) => (
                <span key={index}>
                    {line}
                    {index < description.split('\n').length - 1 && <br />}
                </span>
            ));
    };

    const getJobTypeColor = (jobType) => {
        const colors = {
            'FULL_TIME': 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100',
            'PART_TIME': 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100',
            'CONTRACT': 'bg-purple-100 text-purple-800 dark:bg-purple-800 dark:text-purple-100',
            'INTERNSHIP': 'bg-orange-100 text-orange-800 dark:bg-orange-800 dark:text-orange-100'
        };
        return colors[jobType] || 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100';
    };

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-700">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="animate-pulse">
                        <div className="h-8 bg-gray-300 dark:bg-gray-700 rounded mb-4"></div>
                        <div className="h-64 bg-gray-300 dark:bg-gray-700 rounded mb-4"></div>
                        <div className="h-32 bg-gray-300 dark:bg-gray-700 rounded"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-700">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                        <h3 className="text-lg font-medium text-red-800 dark:text-red-200 mb-2">
                            Error Loading Job Details
                        </h3>
                        <p className="text-red-600 dark:text-red-400">
                            {error.message || 'Failed to load job details. Please try again.'}
                        </p>
                        <button
                            onClick={() => navigate(-1)}
                            className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                        >
                            Go Back
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    if (!job) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-700">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <div className="text-center">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                            Job Not Found
                        </h3>
                        <p className="text-gray-600 dark:text-gray-400 mb-4">
                            The job you're looking for doesn't exist or has been removed.
                        </p>
                        <button
                            onClick={() => navigate('/')}
                            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                            Back to Jobs
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-700">
            {/* Header */}
            <header className="bg-white/30 dark:bg-gray-800/30 backdrop-blur-lg shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center justify-between">
                        <button
                            onClick={() => navigate(-1)}
                            className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white/80 dark:bg-gray-800/80 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                            <ArrowLeftIcon className="h-4 w-4 mr-2" />
                            Back to Jobs
                        </button>
                        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Job Details</h1>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-lg rounded-lg shadow-lg overflow-hidden">
                    {/* Job Header */}
                    <div className="px-6 py-8 border-b border-gray-200 dark:border-gray-700">
                        <div className="flex flex-col md:flex-row md:items-start md:justify-between">
                            <div className="flex-1">
                                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                                    {job.role}
                                </h1>
                                <div className="flex items-center text-lg text-gray-600 dark:text-gray-300 mb-4">
                                    <BuildingOfficeIcon className="h-5 w-5 mr-2" />
                                    {job.company_name}
                                </div>

                                {/* Job Meta Information */}
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                                    <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                                        <MapPinIcon className="h-4 w-4 mr-2" />
                                        {job.location}
                                    </div>
                                    <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                                        <BriefcaseIcon className="h-4 w-4 mr-2" />
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getJobTypeColor(job.job_type)}`}>
                                            {job.job_type.replace('_', ' ')}
                                        </span>
                                    </div>
                                    {job.experience_required && (
                                        <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                                            <ClockIcon className="h-4 w-4 mr-2" />
                                            {job.experience_required}
                                        </div>
                                    )}
                                    {job.compensation && (
                                        <div className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                                            <CurrencyDollarIcon className="h-4 w-4 mr-2" />
                                            {job.compensation}
                                        </div>
                                    )}
                                    <div className="flex items-center text-sm text-gray-600 dark:text-gray-400 md:col-span-2 lg:col-span-1">
                                        <CalendarIcon className="h-4 w-4 mr-2" />
                                        Posted {formatDate(job.created_at)}
                                    </div>
                                </div>

                                {/* Skills */}
                                {job.skills_required && job.skills_required.length > 0 && (
                                    <div className="mb-6">
                                        <div className="flex items-center mb-3">
                                            <TagIcon className="h-4 w-4 mr-2 text-gray-600 dark:text-gray-400" />
                                            <h3 className="text-sm font-medium text-gray-900 dark:text-white">Required Skills</h3>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {job.skills_required.map((skill, index) => (
                                                <span
                                                    key={index}
                                                    className="px-3 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 text-sm font-medium rounded-full"
                                                >
                                                    {skill}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Apply Button */}
                            <div className="mt-6 md:mt-0 md:ml-6">
                                {job.apply_link && (
                                    <a
                                        href={job.apply_link}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors duration-200"
                                    >
                                        Apply Now
                                        <ArrowTopRightOnSquareIcon className="ml-2 h-4 w-4" />
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Job Description */}
                    <div className="px-6 py-8">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                            Job Description
                        </h2>

                        {job.short_description && (
                            <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Summary</h3>
                                <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
                                    {job.short_description}
                                </p>
                            </div>
                        )}

                        {/* <div className="prose prose-gray dark:prose-invert max-w-none">
                            {job.full_description ? (
                                <div className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                                    {formatDescription(job.full_description)}
                                </div>
                            ) : (
                                <p className="text-gray-500 dark:text-gray-400 italic">
                                    No detailed description available.
                                </p>
                            )}
                        </div> */}
                    </div>

                    {/* Footer */}
                    <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                Last updated: {formatDate(job.updated_at)}
                            </div>
                            <div className="mt-2 sm:mt-0">
                                {job.apply_link && (
                                    <a
                                        href={job.apply_link}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                                    >
                                        Apply Now
                                        <ArrowTopRightOnSquareIcon className="ml-2 h-3 w-3" />
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default JobDetails;
