import client from './client';

export const getDeliveryContacts = (params) => {
  return client.get('/delivery/contacts', { params });
};

export const createDeliveryContact = (data) => {
  return client.post('/delivery/contacts', data);
};

export const updateDeliveryContact = (id, data) => {
  return client.put(`/delivery/contacts/${id}`, data);
};

export const deleteDeliveryContact = (id) => {
  return client.delete(`/delivery/contacts/${id}`);
};
