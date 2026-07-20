import client from './client';

export const getSoboRecords = (params) => {
  return client.get('/sobo', { params });
};

export const getSoboStats = () => {
  return client.get('/sobo/stats');
};

export const getSoboRecord = (id) => {
  return client.get(`/sobo/${id}`);
};

export const updateSoboRecord = (id, data) => {
  return client.put(`/sobo/${id}`, data);
};

export const deleteSoboRecord = (id) => {
  return client.delete(`/sobo/${id}`);
};

export const unfollowSoboRecord = (id) => {
  return client.post(`/sobo/${id}/unfollow`);
};

export const getSoboFiles = (id) => {
  return client.get(`/sobo/${id}/files`);
};

export const createSoboFromCase = (caseId) => {
  return client.post(`/sobo/from-case/${caseId}`);
};

export const syncTelegram = () => {
  return client.post('/sobo/sync-telegram');
};

export const checkMail = () => {
  return client.post('/sobo/check-mail');
};
