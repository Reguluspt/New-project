import { useQuery } from '@tanstack/react-query';
import { getStats, getRecentCases, getFilters } from '../api/dashboard';

export function useDashboard(filters = {}) {
  const statsQuery = useQuery({
    queryKey: ['dashboard', 'stats', filters],
    queryFn: async () => {
      const res = await getStats(filters);
      return res.data;
    },
    placeholderData: (prev) => prev,
  });

  const recentCasesQuery = useQuery({
    queryKey: ['dashboard', 'recent-cases', filters],
    queryFn: async () => {
      const res = await getRecentCases(filters);
      return res.data;
    },
    placeholderData: (prev) => prev,
  });

  const filtersQuery = useQuery({
    queryKey: ['dashboard', 'filter-options'],
    queryFn: async () => {
      const res = await getFilters();
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const isLoading = statsQuery.isLoading || recentCasesQuery.isLoading || filtersQuery.isLoading;
  const isError = statsQuery.isError || recentCasesQuery.isError || filtersQuery.isError;
  const error = statsQuery.error || recentCasesQuery.error || filtersQuery.error;

  return {
    stats: statsQuery.data,
    recentCases: recentCasesQuery.data,
    filterOptions: filtersQuery.data,
    isLoading,
    isError,
    error,
    isFetching: statsQuery.isFetching || recentCasesQuery.isFetching,
    refetchAll: () => {
      statsQuery.refetch();
      recentCasesQuery.refetch();
    }
  };
}
