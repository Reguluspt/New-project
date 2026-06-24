import client from './client';

export const listCases = (params) => 
  client.get('/cases', { params });

export const getCase = (id) => 
  client.get(`/cases/${id}`);

export const createCase = (data) => 
  client.post('/cases', data);

export const updateCase = (id, data) => 
  client.put(`/cases/${id}`, data);

export const deleteCase = (id) => 
  client.delete(`/cases/${id}`);

export const updateStatus = (id, status) => 
  client.patch(`/cases/${id}/status`, { status });

export const updatePayment = (id, status) => 
  client.patch(`/cases/${id}/payment`, { payment_status: status });

export const importCases = (file) => { 
  const fd = new FormData(); 
  fd.append('file', file); 
  return client.post('/cases/import', fd); 
};

export const exportCases = (params) => 
  client.get('/cases/export', { params, responseType: 'blob' });

export const getFilters = () => 
  client.get('/cases/filters');

export const getNotes = (id) => 
  client.get(`/cases/${id}/notes`);

export const addNote = (id, note) => 
  client.post(`/cases/${id}/notes`, { note });

export const remindPayment = (id, payload) =>
  client.post(`/cases/${id}/remind-payment`, payload);
