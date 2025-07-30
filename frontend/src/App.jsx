import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ArrowPathIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

import JobList from './components/JobList';
import FilterPanel from './components/FilterPanel';
import ThemeToggle from './components/ThemeToggle';
import { ThemeProvider } from './contexts/ThemeContext';

const queryClient = new QueryClient();

function App() {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefreshJobs = async () => {
    setIsRefreshing(true);
    try {
      await axios.post('http://localhost:8000/api/jobs/refresh/');
      await queryClient.invalidateQueries('jobs');
    } catch (error) {
      console.error('Error refreshing jobs:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleFilterChange = (filters) => {
    // Build query params from filters
    const params = new URLSearchParams();
    if (filters.jobType.length > 0) {
      params.append('job_type', filters.jobType.join(','));
    }
    if (filters.location) {
      params.append('location', filters.location);
    }
    if (filters.experience) {
      params.append('experience', filters.experience);
    }
    if (filters.search) {
      params.append('search', filters.search);
    }

    // Update URL with filters
    window.history.pushState({}, '', `?${params.toString()}`);

    // Refetch jobs with new filters
    queryClient.invalidateQueries('jobs');
  };

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-700">
          <header className="bg-white/30 dark:bg-gray-800/30 backdrop-blur-lg shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
              <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Scraplify</h1>
                <div className="flex items-center space-x-4">
                  <ThemeToggle />
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

          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
              {/* Filters */}
              <FilterPanel
                className="lg:col-span-1"
                onFilterChange={handleFilterChange}
              />

              {/* Job listings */}
              <div className="lg:col-span-3">
                <JobList />
              </div>
            </div>
          </main>
        </div>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
