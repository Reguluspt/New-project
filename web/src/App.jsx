import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Entry from './pages/Entry';
import Cases from './pages/Cases';
import CaseDetail from './pages/CaseDetail';
import Sobo from './pages/Sobo';
import Organizations from './pages/Organizations';
import Delivery from './pages/Delivery';
import Templates from './pages/Templates';
import Settings from './pages/Settings';

// Helper component to redirect root path "/" to dashboard or sobo based on user role
function RootRedirect() {
  const { isGuest } = useAuth();
  if (isGuest) {
    return <Navigate to="/sobo" replace />;
  }
  return <Navigate to="/dashboard" replace />;
}

function App() {
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />

        {/* Protected Monorepo Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <RootRedirect />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Dashboard />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/entry"
          element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Entry />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/cases"
          element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Cases />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/cases/:id"
          element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <CaseDetail />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/sobo"
          element={
            <ProtectedRoute>
              <Layout>
                <Sobo />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/organizations"
          element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Organizations />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/delivery"
          element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Delivery />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/templates"
          element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Templates />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute adminOnly={true}>
              <Layout>
                <Settings />
              </Layout>
            </ProtectedRoute>
          }
        />

        {/* Catch-all Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
