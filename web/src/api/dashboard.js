import client from './client';

export const getStats = (params) => 
  client.get('/dashboard/stats', { params });

export const getRecentCases = (params) => 
  client.get('/dashboard/recent-cases', { params });

export const getFilters = () => 
  client.get('/dashboard/filters');
