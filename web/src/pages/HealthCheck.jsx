import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, Badge, Spin, Alert, Button, Space, Typography } from 'antd';
import { HeartOutlined, ReloadOutlined } from '@ant-design/icons';
import client from '../api/client';

const { Title, Paragraph } = Typography;

export default function HealthCheck() {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await client.get('/health');
      return response.data;
    },
  });

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <Title level={2} style={{ marginBottom: 24 }}>Hệ thống Kiểm tra Health Check</Title>
      <Card
        title={
          <Space>
            <HeartOutlined style={{ color: '#be123c' }} />
            <span>Kết nối Backend API (Flask)</span>
          </Space>
        }
        extra={
          <Button 
            type="primary" 
            icon={<ReloadOutlined spin={isFetching} />} 
            onClick={() => refetch()}
          >
            Kiểm tra lại
          </Button>
        }
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Paragraph>
            Trang này thực hiện gọi API trực tiếp đến <code>/api/health</code> thông qua proxy phát triển của Vite.
          </Paragraph>
          
          {isLoading && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Spin size="large" tip="Đang gửi yêu cầu..." />
            </div>
          )}

          {error && (
            <Alert
              message="Lỗi kết nối API"
              description={error.message || "Không thể kết nối đến Flask backend. Đảm bảo server Flask đang chạy trên cổng 5000."}
              type="error"
              showIcon
            />
          )}

          {data && (
            <Card type="inner" title="Chi tiết Phản hồi từ Server">
              <Space direction="vertical">
                <div>
                  <strong>Trạng thái (Status):</strong>{' '}
                  <Badge status="success" text={data.status} />
                </div>
                {data.version && (
                  <div>
                    <strong>Phiên bản (Version):</strong> {data.version}
                  </div>
                )}
                <div style={{ marginTop: 10 }}>
                  <strong>Phản hồi JSON:</strong>
                  <pre style={{ 
                    background: '#f1f5f9', 
                    padding: 12, 
                    borderRadius: 8, 
                    marginTop: 5,
                    fontFamily: 'monospace',
                    fontSize: '13px'
                  }}>
                    {JSON.stringify(data, null, 2)}
                  </pre>
                </div>
              </Space>
            </Card>
          )}
        </Space>
      </Card>
    </div>
  );
}
