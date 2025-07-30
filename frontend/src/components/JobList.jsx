import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { BriefcaseIcon, MapPinIcon } from '@heroicons/react/24/outline';

const JobCard = ({ job }) => {
    return (
        <div className="bg-white/30 dark:bg-gray-800/30 backdrop-blur-lg rounded-xl p-6 shadow-lg hover:shadow-xl transition-shadow border border-white/20 dark:border-gray-700/20">
            <div className="flex justify-between items-start">
                <div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white">{job.role}</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-300">{job.company_name}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${job.job_type === 'FULL_TIME'
                    ? 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100'
                    : 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100'
                    }`}>
                    {job.job_type === 'FULL_TIME' ? 'Full-time' : 'Internship'}
                </span>
            </div>

            <div className="mt-4 space-y-2">
                <p className="text-sm text-gray-600 dark:text-gray-300 flex items-center">
                    <MapPinIcon className="h-4 w-4 mr-2" />
                    {job.location}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-300 flex items-center">
                    <BriefcaseIcon className="h-4 w-4 mr-2" />
                    {job.experience_required}
                </p>
            </div>

            <p className="mt-4 text-gray-700 dark:text-gray-200">{job.short_description}</p>

            <div className="mt-4 flex flex-wrap gap-2">
                {job.skills_required.map((skill, index) => (
                    <span key={index} className="bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-1 rounded text-xs">
                        {skill}
                    </span>
                ))}
            </div>

            <div className="mt-6 flex space-x-4">
                <button className="flex-1 bg-indigo-600 dark:bg-indigo-500 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 dark:hover:bg-indigo-600 transition-colors">
                    View Details
                </button>
                <a
                    href={job.apply_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 bg-green-600 dark:bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-700 dark:hover:bg-green-600 transition-colors text-center"
                >
                    Apply
                </a>
            </div>
        </div>
    );
};

const JobList = () => {
    const { data: response, isLoading, error } = useQuery({
        queryKey: ['jobs'],
        queryFn: async () => {
            const response = await axios.get('http://localhost:8000/api/jobs/');
            return response.data;
        }
    });

    if (isLoading) {
        return <div className="text-center text-gray-600 dark:text-gray-300">Loading...</div>;
    }

    if (error) {
        return <div className="text-center text-red-600 dark:text-red-400">Error: {error.message}</div>;
    }

    const jobs = response?.results || [];

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {jobs.map(job => (
                <JobCard key={job.id} job={job} />
            ))}
        </div>
    );
};

export default JobList;
