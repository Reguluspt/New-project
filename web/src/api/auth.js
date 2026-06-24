import client from './client';

export const login = (username, password) => 
  client.post('/auth/login', { username, password });

export const logout = () => 
  client.post('/auth/logout');

export const getMe = () => 
  client.get('/auth/me');
