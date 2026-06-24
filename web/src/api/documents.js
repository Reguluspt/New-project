import client from './client';

export const generateDocuments = (caseId, paymentMethod) =>
  client.post(`/cases/${caseId}/documents/generate`, { organization_contract_payment_method: paymentMethod });

export const listDocuments = (caseId) =>
  client.get(`/cases/${caseId}/documents`);

export const previewDocument = (caseId, filename) =>
  client.get(`/cases/${caseId}/documents/${filename}/preview`);

export const downloadDocument = (caseId, filename) =>
  client.get(`/cases/${caseId}/documents/${filename}/download`, { responseType: 'blob' });

export const downloadAllZip = (caseId) =>
  client.get(`/cases/${caseId}/documents/download-all`, { responseType: 'blob' });

export const sendEmail = (caseId, payload) =>
  client.post(`/cases/${caseId}/documents/send-email`, payload);

export const sendPhathanhReply = (caseId, payload) =>
  client.post(`/cases/${caseId}/phathanh/reply`, payload);

export const getDeliveryContacts = () =>
  client.get('/delivery/contacts');

export const saveDelivery = (caseId, payload) =>
  client.post(`/cases/${caseId}/delivery`, payload);
