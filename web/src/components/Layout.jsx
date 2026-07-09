import React, { useState, useEffect, useCallback } from 'react';
import { Layout as AntLayout, Avatar, Button, Space, Drawer } from 'antd';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  DashboardOutlined,
  FileSearchOutlined,
  FolderOutlined,
  FileTextOutlined,
  BankOutlined,
  SendOutlined,
  FileWordOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuOutlined,
  UnorderedListOutlined
} from '@ant-design/icons';

const { Header, Content, Footer } = AntLayout;

export default function Layout({ children }) {
  const { user, logout, isGuest } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Define nav links based on role
  const navItems = isGuest
    ? [
        { path: '/sobo', label: 'Sơ bộ', icon: <FileTextOutlined style={{ fontSize: '16px' }} /> }
      ]
    : [
        { path: '/dashboard', label: 'Dashboard', icon: <DashboardOutlined style={{ fontSize: '16px' }} /> },
        { path: '/entry', label: 'Nhập hồ sơ', icon: <FileSearchOutlined style={{ fontSize: '16px' }} /> },
    { path: '/cases', label: 'Quản lý hồ sơ', icon: <FolderOutlined style={{ fontSize: '16px' }} /> },
    { path: '/tasks', label: 'Công việc', icon: <UnorderedListOutlined style={{ fontSize: '16px' }} /> },
    { path: '/sobo', label: 'Sơ bộ', icon: <FileTextOutlined style={{ fontSize: '16px' }} /> },
        { path: '/organizations', label: 'Tổ chức', icon: <BankOutlined style={{ fontSize: '16px' }} /> },
        { path: '/delivery', label: 'Chuyển phát', icon: <SendOutlined style={{ fontSize: '16px' }} /> },
        { path: '/templates', label: 'Templates', icon: <FileWordOutlined style={{ fontSize: '16px' }} /> },
        { path: '/settings', label: 'Cấu hình', icon: <SettingOutlined style={{ fontSize: '16px' }} /> },
      ];

  const firstLetter = user?.username ? user.username.charAt(0).toUpperCase() : 'U';

  // Global keyboard shortcut: Escape closes mobile menu
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape' && mobileMenuOpen) {
      setMobileMenuOpen(false);
    }
  }, [mobileMenuOpen]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const NavLinkItem = ({ item, onClick }) => (
    <NavLink
      key={item.path}
      to={item.path}
      className={({ isActive }) => `nav-link-item ${isActive ? 'active' : ''}`}
      onClick={onClick}
    >
      {item.icon}
      <span className="nav-link-text">{item.label}</span>
    </NavLink>
  );

  return (
    <AntLayout style={{ minHeight: '100vh', backgroundColor: '#f4faf9' }}>
      {/* Styles block for responsive NavLink, active state, and scrollbar */}
      <style>{`
        .layout-header {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          height: 64px;
          padding: 0 20px;
          background: #ffffff;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
          display: flex;
          align-items: center;
          justify-content: space-between;
          z-index: 1000;
        }
        
        .nav-container {
          display: flex;
          align-items: center;
          height: 64px;
          overflow-x: auto;
          scrollbar-width: none; /* Firefox */
          margin: 0 16px;
          flex-grow: 1;
        }
        
        .nav-container::-webkit-scrollbar {
          display: none; /* Safari and Chrome */
        }

        .nav-link-item {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #64748b;
          text-decoration: none;
          font-weight: 500;
          font-size: 14px;
          height: 64px;
          padding: 0 16px;
          border-bottom: 3px solid transparent;
          transition: all 0.2s ease-in-out;
          white-space: nowrap;
        }

        .nav-link-item:hover {
          color: #006b67;
        }

        .nav-link-item.active {
          color: #006b67;
          border-bottom: 3px solid #006b67;
        }

        .hamburger-btn {
          display: none;
        }

        @media (max-width: 768px) {
          .brand-subtitle {
            display: none;
          }
          .nav-container {
            display: none;
          }
          .hamburger-btn {
            display: flex;
          }
          .user-name-text {
            display: none;
          }
        }

        /* Mobile drawer nav links */
        .mobile-nav-link {
          display: flex;
          align-items: center;
          gap: 12px;
          color: #374151;
          text-decoration: none;
          font-weight: 500;
          font-size: 15px;
          padding: 12px 16px;
          border-radius: 8px;
          transition: background 0.15s ease;
        }
        .mobile-nav-link:hover,
        .mobile-nav-link.active {
          background: #e6f4f2;
          color: #006b67;
        }
      `}</style>

      {/* Header Container */}
      <Header className="layout-header">
        {/* Brand / Logo */}
        <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
          <img
            src="/cenvalue-logo.png"
            alt="CEN VALUE"
            style={{ display: 'block', height: 36, width: 'auto', maxWidth: 180, objectFit: 'contain' }}
          />
        </div>

        {/* Desktop Navigation Bar */}
        <div className="nav-container">
          {navItems.map((item) => (
            <NavLinkItem key={item.path} item={item} />
          ))}
        </div>

        {/* User Info & Logout */}
        <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
          <Space size="middle">
            <Space size="small">
              <Avatar style={{ backgroundColor: '#007f7a', fontWeight: 'bold' }} size="default">
                {firstLetter}
              </Avatar>
              <span className="user-name-text" style={{ fontWeight: 600, color: '#0f172a' }}>
                {user?.username}
              </span>
            </Space>
            <Button
              type="text"
              danger
              icon={<LogoutOutlined />}
              onClick={handleLogout}
              style={{ fontWeight: 500, display: 'flex', alignItems: 'center' }}
            >
              <span className="nav-link-text">Đăng xuất</span>
            </Button>
            {/* Hamburger button (mobile only) */}
            <Button
              className="hamburger-btn"
              type="text"
              icon={<MenuOutlined style={{ fontSize: 20 }} />}
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Mở menu điều hướng"
            />
          </Space>
        </div>
      </Header>

      {/* Mobile Navigation Drawer */}
      <Drawer
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Avatar style={{ backgroundColor: '#007f7a', fontWeight: 'bold' }}>
              {firstLetter}
            </Avatar>
            <span style={{ fontWeight: 700, color: '#0f172a' }}>{user?.username}</span>
          </div>
        }
        placement="left"
        onClose={() => setMobileMenuOpen(false)}
        open={mobileMenuOpen}
        width={260}
        styles={{ body: { padding: '8px 12px' } }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
          <div style={{ borderTop: '1px solid #e5e7eb', marginTop: 12, paddingTop: 12 }}>
            <button
              onClick={handleLogout}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                color: '#dc2626',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: 15,
                padding: '12px 16px',
                borderRadius: 8,
              }}
            >
              <LogoutOutlined />
              <span>Đăng xuất</span>
            </button>
          </div>
        </div>
      </Drawer>

      {/* Main Content Area */}
      <Content style={{ marginTop: 64, padding: '24px 20px', minHeight: 'calc(100vh - 64px - 70px)' }}>
        <div style={{ maxWidth: 1920, margin: '0 auto', width: '100%' }}>
          {children}
        </div>
      </Content>

      <Footer style={{ textAlign: 'center', color: '#64748b', background: '#f4faf9', padding: '20px 0 30px' }}>
        Hệ thống Thẩm định Giá Cenvalue ©2026 - SPA Migration
      </Footer>
    </AntLayout>
  );
}
