import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { Spin } from 'antd';

export default function ProtectedRoute({ children, adminOnly = false }) {
  const { isLoading, isAuthenticated, isGuest } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        background: '#f5f7fb'
      }}>
        <Spin size="large" tip="Đang xác thực tài khoản..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If the user is a guest, they are only allowed on "/sobo".
  // If they attempt to access any other route, redirect them to "/sobo".
  if (isGuest && location.pathname !== '/sobo') {
    return <Navigate to="/sobo" replace />;
  }

  // If a route requires admin privileges and current user is guest, redirect to "/sobo"
  if (adminOnly && isGuest) {
    return <Navigate to="/sobo" replace />;
  }

  return children;
}
