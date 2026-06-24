import React, { useState } from 'react';
import { Form, Input, Button, Card, Alert, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const { Title, Text } = Typography;

export default function Login() {
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect back to original route or appropriate landing page
  const from = location.state?.from?.pathname || '/';

  const onFinish = async (values) => {
    setError(null);
    setSubmitting(true);
    try {
      const user = await login(values.username.trim(), values.password);
      if (user.role === 'guest') {
        navigate('/sobo', { replace: true });
      } else {
        // If coming from login/sobo, default to dashboard, otherwise go back
        const target = from === '/login' || from === '/sobo' ? '/dashboard' : from;
        navigate(target, { replace: true });
      }
    } catch (err) {
      setError(
        err.response?.data?.error ||
        "Không thể kết nối máy chủ. Vui lòng thử lại sau."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      backgroundColor: '#f5f7fb',
      padding: '20px',
    }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }} className="login-brand">
        <Title level={1} style={{ 
          color: '#0f6cbd', 
          fontSize: '28px', 
          fontWeight: 750, 
          margin: 0,
          fontFamily: '"Segoe UI", system-ui, -apple-system, sans-serif'
        }} className="login-title">
          Hệ Thống Thẩm Định
        </Title>
        <Text style={{ 
          color: '#64748b', 
          fontSize: '14px', 
          marginTop: 8, 
          display: 'inline-block' 
        }} className="login-subtitle">
          Đăng nhập để tiếp tục quản lý hồ sơ
        </Text>
      </div>

      <Card 
        style={{ 
          width: '100%', 
          maxWidth: 420, 
          borderRadius: 8, 
          boxShadow: '0 18px 50px rgba(22,39,70,0.10)',
          border: 'none'
        }}
        styles={{ body: { padding: '32px 24px' } }}
      >
        <Title level={3} style={{ 
          textAlign: 'center', 
          marginBottom: 24, 
          fontSize: '20px', 
          fontWeight: 600 
        }}>
          Đăng nhập
        </Title>

        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: 20 }}
          />
        )}

        <Form
          name="login_form"
          onFinish={onFinish}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Vui lòng nhập tên tài khoản!' }]}
          >
            <Input 
              prefix={<UserOutlined style={{ color: '#94a3b8' }} />} 
              placeholder="Tên tài khoản" 
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Vui lòng nhập mật khẩu!' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#94a3b8' }} />}
              placeholder="Mật khẩu"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={submitting} 
              style={{ width: '100%', borderRadius: 8, height: 45, fontWeight: 'bold' }}
            >
              Đăng nhập
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
