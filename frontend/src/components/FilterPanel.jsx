import React, { useState } from 'react';
import { Dialog } from '@headlessui/react';
import { XMarkIcon, FunnelIcon } from '@heroicons/react/24/outline';

const FilterPanel = ({ onFilterChange, className = '' }) => {
    const [filters, setFilters] = useState({
        jobType: [],
        location: '',
        experience: '',
        search: '',
    });

    const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

    const handleFilterChange = (key, value) => {
        const newFilters = { ...filters, [key]: value };
        setFilters(newFilters);
        onFilterChange(newFilters);
    };

    const handleJobTypeToggle = (type) => {
        const newJobTypes = filters.jobType.includes(type)
            ? filters.jobType.filter(t => t !== type)
            : [...filters.jobType, type];

        handleFilterChange('jobType', newJobTypes);
    };

    const FiltersContent = () => (
        <>
            {/* Search */}
            <div className="border-b border-gray-200 dark:border-gray-600 pb-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">Search</h3>
                <div className="mt-2">
                    <input
                        type="text"
                        placeholder="Search by role or company"
                        className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 placeholder-gray-500 dark:placeholder-gray-400"
                        value={filters.search}
                        onChange={(e) => handleFilterChange('search', e.target.value)}
                    />
                </div>
            </div>

            {/* Job Type */}
            <div className="border-b border-gray-200 dark:border-gray-600 py-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">Job Type</h3>
                <div className="mt-2 space-y-2">
                    <label className="flex items-center">
                        <input
                            type="checkbox"
                            checked={filters.jobType.includes('FULL_TIME')}
                            onChange={() => handleJobTypeToggle('FULL_TIME')}
                            className="h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-indigo-600 dark:text-indigo-400"
                        />
                        <span className="ml-2 text-gray-900 dark:text-white">Full-time</span>
                    </label>
                    <label className="flex items-center">
                        <input
                            type="checkbox"
                            checked={filters.jobType.includes('INTERNSHIP')}
                            onChange={() => handleJobTypeToggle('INTERNSHIP')}
                            className="h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-indigo-600 dark:text-indigo-400"
                        />
                        <span className="ml-2 text-gray-900 dark:text-white">Internship</span>
                    </label>
                </div>
            </div>

            {/* Location */}
            <div className="border-b border-gray-200 dark:border-gray-600 py-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">Location</h3>
                <div className="mt-2">
                    <input
                        type="text"
                        placeholder="Filter by location"
                        className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 placeholder-gray-500 dark:placeholder-gray-400"
                        value={filters.location}
                        onChange={(e) => handleFilterChange('location', e.target.value)}
                    />
                </div>
            </div>

            {/* Experience */}
            <div className="py-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">Experience</h3>
                <div className="mt-2">
                    <input
                        type="text"
                        placeholder="Years of experience"
                        className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white px-3 py-2 placeholder-gray-500 dark:placeholder-gray-400"
                        value={filters.experience}
                        onChange={(e) => handleFilterChange('experience', e.target.value)}
                    />
                </div>
            </div>
        </>
    );

    return (
        <div className={className}>
            {/* Mobile filter dialog */}
            <Dialog as="div" className="lg:hidden" open={mobileFiltersOpen} onClose={setMobileFiltersOpen}>
                <div className="fixed inset-0 z-40 flex">
                    <Dialog.Panel className="relative ml-auto flex h-full w-full max-w-xs flex-col overflow-y-auto bg-white dark:bg-gray-800 py-4 pb-6 shadow-xl">
                        <div className="flex items-center justify-between px-4">
                            <h2 className="text-lg font-medium text-gray-900 dark:text-white">Filters</h2>
                            <button
                                type="button"
                                className="text-gray-400 dark:text-gray-300 hover:text-gray-500 dark:hover:text-gray-200"
                                onClick={() => setMobileFiltersOpen(false)}
                            >
                                <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                            </button>
                        </div>

                        <div className="px-4">
                            <FiltersContent />
                        </div>
                    </Dialog.Panel>
                </div>
            </Dialog>

            {/* Desktop filters */}
            <div className="hidden lg:block">
                <FiltersContent />
            </div>

            {/* Mobile filter button */}
            <button
                type="button"
                className="lg:hidden fixed bottom-4 right-4 inline-flex items-center rounded-full bg-indigo-600 dark:bg-indigo-500 p-3 text-white shadow-lg hover:bg-indigo-700 dark:hover:bg-indigo-600"
                onClick={() => setMobileFiltersOpen(true)}
            >
                <FunnelIcon className="h-6 w-6" aria-hidden="true" />
            </button>
        </div>
    );
};

export default FilterPanel;
