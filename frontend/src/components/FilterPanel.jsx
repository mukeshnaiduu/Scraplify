import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Dialog } from '@headlessui/react';
import {
    XMarkIcon,
    FunnelIcon,
    MagnifyingGlassIcon,
    MapPinIcon,
    BriefcaseIcon,
    CurrencyDollarIcon
} from '@heroicons/react/24/outline';

const FilterPanel = ({ filters, onFilterChange, allJobs = [] }) => {
    const [localFilters, setLocalFilters] = useState(filters);
    const [searchInput, setSearchInput] = useState(filters.search || '');
    const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
    const [skillSearchTerm, setSkillSearchTerm] = useState('');
    const [showSkillDropdown, setShowSkillDropdown] = useState(false);

    const debounceTimeoutRef = useRef(null);

    // Extract suggestions from job data
    const suggestions = useMemo(() => {
        if (!allJobs || allJobs.length === 0) {
            return { locations: [], skills: [], companies: [] };
        }

        const locations = [...new Set(
            allJobs.map(job => job.location).filter(Boolean)
        )].sort();

        const skills = [...new Set(
            allJobs.flatMap(job => job.skills_required || [])
        )].sort();

        const companies = [...new Set(
            allJobs.map(job => job.company_name).filter(Boolean)
        )].sort();

        return { locations, skills, companies };
    }, [allJobs]);

    // Filtered skill suggestions
    const filteredSkillSuggestions = useMemo(() => {
        if (!skillSearchTerm.trim()) return suggestions.skills.slice(0, 8);

        const term = skillSearchTerm.toLowerCase();
        return suggestions.skills
            .filter(skill => skill.toLowerCase().includes(term))
            .slice(0, 8);
    }, [suggestions.skills, skillSearchTerm]);

    // Debounced filter updates
    useEffect(() => {
        if (debounceTimeoutRef.current) {
            clearTimeout(debounceTimeoutRef.current);
        }

        debounceTimeoutRef.current = setTimeout(() => {
            const updatedFilters = {
                ...localFilters,
                search: searchInput
            };
            onFilterChange(updatedFilters);
        }, 300);

        return () => {
            if (debounceTimeoutRef.current) {
                clearTimeout(debounceTimeoutRef.current);
            }
        };
    }, [searchInput, localFilters, onFilterChange]);

    // Update local state when external filters change
    useEffect(() => {
        setLocalFilters(filters);
        setSearchInput(filters.search || '');
    }, [filters]);

    const handleFilterUpdate = (key, value) => {
        const newFilters = { ...localFilters, [key]: value };
        setLocalFilters(newFilters);

        // Immediate update for non-search filters
        if (key !== 'search') {
            onFilterChange(newFilters);
        }
    };

    const handleJobTypeToggle = (type) => {
        const currentTypes = localFilters.jobType || [];
        const newTypes = currentTypes.includes(type)
            ? currentTypes.filter(t => t !== type)
            : [...currentTypes, type];

        handleFilterUpdate('jobType', newTypes);
    };

    const handleSkillAdd = (skill) => {
        const currentSkills = localFilters.skills || [];
        if (!currentSkills.includes(skill)) {
            handleFilterUpdate('skills', [...currentSkills, skill]);
        }
        setSkillSearchTerm('');
        setShowSkillDropdown(false);
    };

    const handleSkillRemove = (skillToRemove) => {
        const currentSkills = localFilters.skills || [];
        handleFilterUpdate('skills', currentSkills.filter(skill => skill !== skillToRemove));
    };

    const handleSalaryChange = (type, value) => {
        const newSalaryRange = {
            ...localFilters.salaryRange,
            [type]: value === '' ? '' : parseInt(value)
        };
        handleFilterUpdate('salaryRange', newSalaryRange);
    };

    const clearAllFilters = () => {
        const clearedFilters = {
            jobType: [],
            location: '',
            experience: '',
            search: '',
            skills: [],
            salaryRange: { min: '', max: '' }
        };
        setLocalFilters(clearedFilters);
        setSearchInput('');
        onFilterChange(clearedFilters);
    };

    const getActiveFilterCount = () => {
        const { jobType = [], location, experience, search, skills = [], salaryRange = {} } = localFilters;
        return (
            jobType.length +
            (location ? 1 : 0) +
            (experience ? 1 : 0) +
            (search ? 1 : 0) +
            skills.length +
            (salaryRange.min || salaryRange.max ? 1 : 0)
        );
    };

    const jobTypeOptions = [
        { value: 'FULL_TIME', label: 'Full-time' },
        { value: 'PART_TIME', label: 'Part-time' },
        { value: 'INTERNSHIP', label: 'Internship' },
        { value: 'CONTRACT', label: 'Contract' }
    ];

    const experienceOptions = [
        { value: '0', label: 'Fresh Graduate' },
        { value: '1', label: '1+ Years' },
        { value: '2', label: '2+ Years' },
        { value: '3', label: '3+ Years' },
        { value: '5', label: '5+ Years' },
    ];

    const FiltersContent = () => (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-600">
                <div className="flex items-center space-x-2">
                    <FunnelIcon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                        Filters
                    </h3>
                    {getActiveFilterCount() > 0 && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-800 dark:text-indigo-200">
                            {getActiveFilterCount()}
                        </span>
                    )}
                </div>
                {getActiveFilterCount() > 0 && (
                    <button
                        onClick={clearAllFilters}
                        className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                    >
                        Clear all
                    </button>
                )}
            </div>

            {/* Search */}
            <div className="space-y-3">
                <label className="text-sm font-medium text-gray-900 dark:text-white flex items-center">
                    <MagnifyingGlassIcon className="h-4 w-4 mr-2" />
                    Search Jobs
                </label>
                <div className="relative">
                    <input
                        type="text"
                        placeholder="Search by role, company, or keywords..."
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-colors"
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                    />
                    {searchInput && (
                        <button
                            onClick={() => setSearchInput('')}
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        >
                            <XMarkIcon className="h-4 w-4" />
                        </button>
                    )}
                </div>
            </div>

            {/* Job Type */}
            <div className="space-y-3">
                <label className="text-sm font-medium text-gray-900 dark:text-white flex items-center">
                    <BriefcaseIcon className="h-4 w-4 mr-2" />
                    Job Type
                </label>
                <div className="space-y-2">
                    {jobTypeOptions.map(option => (
                        <label key={option.value} className="flex items-center cursor-pointer">
                            <input
                                type="checkbox"
                                checked={(localFilters.jobType || []).includes(option.value)}
                                onChange={() => handleJobTypeToggle(option.value)}
                                className="rounded border-gray-300 dark:border-gray-600 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0"
                            />
                            <span className="ml-3 text-sm text-gray-700 dark:text-gray-300">
                                {option.label}
                            </span>
                        </label>
                    ))}
                </div>
            </div>

            {/* Location */}
            <div className="space-y-3">
                <label className="text-sm font-medium text-gray-900 dark:text-white flex items-center">
                    <MapPinIcon className="h-4 w-4 mr-2" />
                    Location
                </label>
                <input
                    type="text"
                    placeholder="Enter location or 'Remote'"
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    value={localFilters.location || ''}
                    onChange={(e) => handleFilterUpdate('location', e.target.value)}
                />
                {suggestions.locations.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                        {suggestions.locations.slice(0, 3).map(location => (
                            <button
                                key={location}
                                onClick={() => handleFilterUpdate('location', location)}
                                className="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-indigo-100 dark:hover:bg-indigo-900 transition-colors"
                            >
                                {location}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Experience */}
            <div className="space-y-3">
                <label className="text-sm font-medium text-gray-900 dark:text-white">
                    Experience Level
                </label>
                <select
                    value={localFilters.experience || ''}
                    onChange={(e) => handleFilterUpdate('experience', e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                    <option value="">Any Experience</option>
                    {experienceOptions.map(option => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
            </div>

            {/* Skills */}
            <div className="space-y-3">
                <label className="text-sm font-medium text-gray-900 dark:text-white">
                    Skills
                </label>

                {/* Selected Skills */}
                {localFilters.skills && localFilters.skills.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                        {localFilters.skills.map(skill => (
                            <span
                                key={skill}
                                className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-800 dark:text-indigo-200"
                            >
                                {skill}
                                <button
                                    onClick={() => handleSkillRemove(skill)}
                                    className="ml-2 text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-200"
                                >
                                    <XMarkIcon className="h-3 w-3" />
                                </button>
                            </span>
                        ))}
                    </div>
                )}

                {/* Skill Search */}
                <div className="relative">
                    <input
                        type="text"
                        placeholder="Add skills (React, Python, etc.)"
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        value={skillSearchTerm}
                        onChange={(e) => setSkillSearchTerm(e.target.value)}
                        onFocus={() => setShowSkillDropdown(true)}
                        onBlur={() => setTimeout(() => setShowSkillDropdown(false), 200)}
                    />

                    {/* Skill Suggestions Dropdown */}
                    {showSkillDropdown && filteredSkillSuggestions.length > 0 && (
                        <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                            {filteredSkillSuggestions.map(skill => (
                                <button
                                    key={skill}
                                    onClick={() => handleSkillAdd(skill)}
                                    className="w-full px-4 py-2 text-left text-sm text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                    disabled={(localFilters.skills || []).includes(skill)}
                                >
                                    {skill}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Salary Range */}
            <div className="space-y-3">
                <label className="text-sm font-medium text-gray-900 dark:text-white flex items-center">
                    <CurrencyDollarIcon className="h-4 w-4 mr-2" />
                    Salary Range (Annual)
                </label>
                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                            Min Salary
                        </label>
                        <input
                            type="number"
                            placeholder="30000"
                            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                            value={localFilters.salaryRange?.min || ''}
                            onChange={(e) => handleSalaryChange('min', e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                            Max Salary
                        </label>
                        <input
                            type="number"
                            placeholder="150000"
                            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                            value={localFilters.salaryRange?.max || ''}
                            onChange={(e) => handleSalaryChange('max', e.target.value)}
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    return (
        <>
            {/* Mobile Filter Button */}
            <div className="lg:hidden mb-4">
                <button
                    onClick={() => setMobileFiltersOpen(true)}
                    className="flex items-center justify-center w-full px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                    <FunnelIcon className="h-5 w-5 mr-2" />
                    Filters
                    {getActiveFilterCount() > 0 && (
                        <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-800 dark:text-indigo-200">
                            {getActiveFilterCount()}
                        </span>
                    )}
                </button>
            </div>

            {/* Desktop Filters */}
            <div className="hidden lg:block">
                <FiltersContent />
            </div>

            {/* Mobile Filter Dialog */}
            <Dialog
                open={mobileFiltersOpen}
                onClose={setMobileFiltersOpen}
                className="relative z-50 lg:hidden"
            >
                <div className="fixed inset-0 bg-black bg-opacity-25" />
                <div className="fixed inset-0 z-50 overflow-y-auto">
                    <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
                        <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-sm sm:p-6">
                            <div className="absolute right-0 top-0 pr-4 pt-4">
                                <button
                                    onClick={() => setMobileFiltersOpen(false)}
                                    className="rounded-md bg-white dark:bg-gray-800 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                                >
                                    <XMarkIcon className="h-6 w-6" />
                                </button>
                            </div>
                            <FiltersContent />
                        </Dialog.Panel>
                    </div>
                </div>
            </Dialog>
        </>
    );
};

export default FilterPanel;
