import client from './client';

export const uploadFiles = (formData, onProgress) => {
  return client.post('/entry/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    }
  });
};

export const pageImageUrl = (uploadId, fileId, pageNum, rotation = 0) => {
  return `/api/entry/uploads/${uploadId}/${fileId}/page/${pageNum}?rotation=${rotation}`;
};

export const extractFields = (payload) => {
  return client.post('/entry/extract', payload);
};

export const getFormOptions = () => {
  return client.get('/entry/form-options');
};

export const addFormOption = (field, value) => {
  return client.post('/entry/form-options/custom', { field, value });
};

export const saveCase = (payload) => {
  return client.post('/entry/save', payload);
};

export const downloadExcel = (params) => {
  return client.get('/entry/excel-download', { params, responseType: 'blob' });
};

export const sendEmail = (payload) => {
  return client.post('/entry/send-email', { payload });
};

export const submitWeb = (payload) => {
  return client.post('/entry/submit-web', { payload });
};
