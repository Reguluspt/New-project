import client from './client';

export const getOrganizations = (params) => {
  return client.get('/organizations', { params });
};

export const createOrganization = (data) => {
  return client.post('/organizations', data);
};

export const updateOrganization = (id, data) => {
  return client.put(`/organizations/${id}`, data);
};

export const deleteOrganization = (id) => {
  return client.delete(`/organizations/${id}`);
};

export const mergeOrganizations = (sourceId, targetId) => {
  return client.post('/organizations/merge', { source_id: sourceId, target_id: targetId });
};

export const extractOrganizationAi = (formData) => {
  return client.post('/organizations/ai-extract', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};
