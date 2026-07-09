import client from './client';

export const getSettings = () => {
  return client.get('/settings');
};

export const updatePaths = (paths) => {
  return client.put('/settings/paths', paths);
};

export const updateWebmailConfig = (payload) => {
  return client.put('/settings/webmail', payload);
};

export const getOAuthUrl = (provider, redirectUri) => {
  return client.get(`/settings/oauth/${provider}/auth-url`, {
    params: { redirect_uri: redirectUri },
  });
};

export const exchangeOAuthCode = (payload) => {
  return client.post('/settings/oauth/callback', payload);
};

export const disconnectOAuth = (provider) => {
  return client.delete(`/settings/oauth/${provider}`);
};

export const updateOAuthConfig = (payload) => {
  return client.put('/settings/oauth-config', payload);
};

export const getAiConfig = () => {
  return client.get('/settings/ai-config');
};

export const updateAiConfig = (payload) => {
  return client.put('/settings/ai-config', payload);
};

export const restartAiServices = () => {
  return client.post('/settings/ai-config/restart-services');
};

export const createBackup = () => {
  return client.post('/settings/backup');
};

export const downloadBackupUrl = () => {
  return '/api/settings/backup/download';
};

export const restoreBackup = (formData) => {
  return client.post('/settings/backup/restore', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};
