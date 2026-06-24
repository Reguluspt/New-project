import React from 'react';
import { Result, Button, Typography } from 'antd';

const { Text } = Typography;

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
  }

  handleReset() {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/';
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f5f7fb',
          padding: 24
        }}>
          <div style={{ maxWidth: 560, width: '100%' }}>
            <Result
              status="error"
              title="Ứng dụng gặp lỗi không mong muốn"
              subTitle="Đã xảy ra lỗi nghiêm trọng. Vui lòng tải lại trang hoặc liên hệ quản trị viên."
              extra={[
                <Button
                  key="reload"
                  type="primary"
                  onClick={() => this.handleReset()}
                  style={{ borderRadius: 6 }}
                >
                  Tải lại trang
                </Button>,
                <Button
                  key="back"
                  onClick={() => window.history.back()}
                  style={{ borderRadius: 6 }}
                >
                  Quay lại
                </Button>
              ]}
            />
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div style={{
                marginTop: 24,
                padding: '12px 16px',
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: 8
              }}>
                <Text type="danger" style={{ fontSize: 13, fontFamily: 'monospace', whiteSpace: 'pre-wrap', display: 'block' }}>
                  {this.state.error.toString()}
                  {this.state.errorInfo?.componentStack}
                </Text>
              </div>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
