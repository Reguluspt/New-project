import client from './client';

export const getTemplates = () => {
  return client.get('/templates');
};

export const getTemplateDetail = (name) => {
  return client.get(`/templates/${name}`);
};

export const uploadTemplateVersion = (name, formData) => {
  return client.put(`/templates/${name}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

export const getTemplateHistory = (name) => {
  return client.get(`/templates/${name}/history`);
};

export const downloadTemplate = (name) => {
  return client.get(`/templates/${name}/download`, { responseType: 'blob' });
};

