import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Card,
  Typography,
  Tabs,
  Form,
  Input,
  Button,
  Space,
  Row,
  Col,
  Tag,
  Statistic,
  Upload,
  message,
  Popconfirm,
  Badge,
  Descriptions,
  Select
} from 'antd';
import {
  FolderOpenOutlined,
  GoogleOutlined,
  WindowsOutlined,
  CloudUploadOutlined,
  CloudDownloadOutlined,
  ReloadOutlined,
  SlidersOutlined,
  SaveOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  KeyOutlined
} from '@ant-design/icons';
import {
  getSettings,
  updatePaths,
  getOAuthUrl,
  exchangeOAuthCode,
  disconnectOAuth,
  updateOAuthConfig,
  getAiConfig,
  updateAiConfig,
  restartAiServices,
  createBackup,
  downloadBackupUrl,
  restoreBackup
} from '../api/settings';

const { Title, Paragraph, Text } = Typography;

export default function Settings() {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Settings values state
  const [settings, setSettings] = useState({
    paths: {
      excel_template: '',
      individual_template_dir: '',
      organization_template_dir: '',
      output_dir: ''
    },
    oauth: {
      google: { connected: false, email: '', client_id: '', client_secret: '' },
      outlook: { connected: false, email: '', client_id: '', client_secret: '', tenant: 'common', sender_email: '' },
      redirect_uri: ''
    },
    services: {
      telegram: 'stopped',
      mail_listener: 'stopped',
      ngrok: 'stopped'
    },
    system: {
      version: '2.0',
      db_size: '0.00 MB'
    }
  });

  const [loading, setLoading] = useState(false);
  const [savingPaths, setSavingPaths] = useState(false);
  const [savingGoogle, setSavingGoogle] = useState(false);
  const [savingOutlook, setSavingOutlook] = useState(false);
  const [savingRedirect, setSavingRedirect] = useState(false);
  const [savingSobo, setSavingSobo] = useState(false);
  const [savingAi, setSavingAi] = useState(false);
  const [restartingAiServices, setRestartingAiServices] = useState(false);
  const [backingUp, setBackingUp] = useState(false);
  const [restoring, setRestoring] = useState(false);

  const [pathForm] = Form.useForm();
  const [googleForm] = Form.useForm();
  const [outlookForm] = Form.useForm();
  const [redirectForm] = Form.useForm();
  const [soboForm] = Form.useForm();
  const [aiForm] = Form.useForm();
  const [aiConfig, setAiConfig] = useState({ configured: false, key_suffix: '', model: 'gemini-2.5-flash' });

  // Load settings from API
  const fetchSettings = async () => {
    setLoading(true);
    try {
      const [res, aiRes] = await Promise.all([getSettings(), getAiConfig()]);
      setSettings(res.data);
      const gemini = aiRes.data.gemini;
      setAiConfig(gemini);
      aiForm.setFieldsValue({ gemini_model: gemini.model });
      pathForm.setFieldsValue(res.data.paths);
      if (res.data.oauth) {
        redirectForm.setFieldsValue({
          redirect_uri: res.data.oauth.redirect_uri || ''
        });
        googleForm.setFieldsValue({
          client_id: res.data.oauth.google?.client_id || '',
          client_secret: res.data.oauth.google?.client_secret || ''
        });
        outlookForm.setFieldsValue({
          client_id: res.data.oauth.outlook?.client_id || '',
          client_secret: res.data.oauth.outlook?.client_secret || '',
          tenant: res.data.oauth.outlook?.tenant || 'common',
          sender_email: res.data.oauth.outlook?.sender_email || ''
        });
        if (res.data.oauth.sobo_email) {
          soboForm.setFieldsValue({
            provider: res.data.oauth.sobo_email.provider || 'google',
            mail_username: res.data.oauth.sobo_email.mail_username || '',
            mail_from: res.data.oauth.sobo_email.mail_from || ''
          });
        }
      }
    } catch (err) {
      console.error(err);
      message.error('Không thể tải cấu hình hệ thống');
    } finally {
      setLoading(false);
    }
  };

  const handleAiSave = async () => {
    try {
      const values = await aiForm.validateFields();
      setSavingAi(true);
      const res = await updateAiConfig(values);
      setAiConfig(res.data.gemini);
      aiForm.setFieldValue('gemini_api_key', '');
      message.success('Đã lưu cấu hình Gemini API. Key không được trả về trình duyệt.');
    } catch (err) {
      if (err.name !== 'ValidationError') {
        message.error('Lỗi khi lưu Gemini API: ' + (err.response?.data?.error || err.message));
      }
    } finally {
      setSavingAi(false);
    }
  };

  const handleAiServicesRestart = async () => {
    try {
      setRestartingAiServices(true);
      await restartAiServices();
      message.success('Đã khởi động lại Telegram Bot và Mail Listener.');
    } catch (err) {
      message.error('Không thể khởi động lại dịch vụ AI: ' + (err.response?.data?.error || err.message));
    } finally {
      setRestartingAiServices(false);
    }
  };

  // Handle OAuth Code callback from URL parameters
  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state'); // state maps to provider name
    
    if (code && state) {
      const exchangeCode = async () => {
        const hide = message.loading(`Đang liên kết tài khoản OAuth2 ${state.toUpperCase()}...`, 0);
        try {
          await exchangeOAuthCode({
            provider: state,
            code: code,
            redirect_uri: window.location.origin + window.location.pathname
          });
          message.success(`🎉 Liên kết tài khoản ${state.toUpperCase()} thành công!`);
          // Clear query params
          setSearchParams({});
          fetchSettings();
        } catch (err) {
          console.error(err);
          message.error('Lỗi liên kết OAuth2: ' + (err.response?.data?.error || err.message));
        } finally {
          hide();
        }
      };
      
      exchangeCode();
    } else {
      fetchSettings();
    }
  }, [searchParams]);

  // Save Paths configuration
  const handlePathsSave = async () => {
    try {
      const values = await pathForm.validateFields();
      setSavingPaths(true);
      await updatePaths(values);
      message.success('Đã lưu cấu hình đường dẫn thành công!');
      fetchSettings();
    } catch (err) {
      if (err.name !== 'ValidationError') {
        message.error('Lỗi khi lưu cấu hình: ' + (err.response?.data?.error || err.message));
      }
    } finally {
      setSavingPaths(false);
    }
  };

  // Save Google OAuth2 configuration
  const handleGoogleSave = async () => {
    try {
      const values = await googleForm.validateFields();
      setSavingGoogle(true);
      await updateOAuthConfig({ google: values });
      message.success('Đã lưu cấu hình Google Workspace thành công!');
      fetchSettings();
    } catch (err) {
      if (err.name !== 'ValidationError') {
        message.error('Lỗi khi lưu cấu hình Google: ' + (err.response?.data?.error || err.message));
      }
    } finally {
      setSavingGoogle(false);
    }
  };

  // Save Outlook OAuth2 configuration
  const handleOutlookSave = async () => {
    try {
      const values = await outlookForm.validateFields();
      setSavingOutlook(true);
      await updateOAuthConfig({ outlook: values });
      message.success('Đã lưu cấu hình Microsoft Outlook thành công!');
      fetchSettings();
    } catch (err) {
      if (err.name !== 'ValidationError') {
        message.error('Lỗi khi lưu cấu hình Outlook: ' + (err.response?.data?.error || err.message));
      }
    } finally {
      setSavingOutlook(false);
    }
  };

  // Save Redirect URI
  const handleRedirectSave = async () => {
    try {
      const values = await redirectForm.validateFields();
      setSavingRedirect(true);
      await updateOAuthConfig(values);
      message.success('Đã lưu Redirect URI thành công!');
      fetchSettings();
    } catch (err) {
      if (err.name !== 'ValidationError') {
        message.error('Lỗi khi lưu Redirect URI: ' + (err.response?.data?.error || err.message));
      }
    } finally {
      setSavingRedirect(false);
    }
  };

  // Save Sobo Email configuration
  const handleSoboSave = async () => {
    try {
      const values = await soboForm.validateFields();
      setSavingSobo(true);
      await updateOAuthConfig({ sobo_email: values });
      message.success('Đã lưu cấu hình mail Sơ bộ thành công!');
      fetchSettings();
    } catch (err) {
      if (err.name !== 'ValidationError') {
        message.error('Lỗi khi lưu cấu hình mail Sơ bộ: ' + (err.response?.data?.error || err.message));
      }
    } finally {
      setSavingSobo(false);
    }
  };

  // Connect OAuth
  const handleOAuthConnect = async (provider) => {
    try {
      const redirectUri = redirectForm.getFieldValue('redirect_uri') || (window.location.origin + window.location.pathname);
      const res = await getOAuthUrl(provider, redirectUri);
      if (res.data.url) {
        // Redirect user to provider consent screen
        window.location.href = res.data.url;
      } else {
        message.error('Không tạo được liên kết kết nối OAuth');
      }
    } catch (err) {
      message.error('Lỗi tạo liên kết OAuth: ' + (err.response?.data?.error || err.message));
    }
  };

  // Disconnect OAuth
  const handleOAuthDisconnect = async (provider) => {
    try {
      await disconnectOAuth(provider);
      message.success(`Đã hủy liên kết tài khoản ${provider.toUpperCase()}`);
      fetchSettings();
    } catch (err) {
      message.error(`Lỗi khi hủy liên kết ${provider.toUpperCase()}`);
    }
  };

  // Create & Download Backup
  const handleBackup = async () => {
    setBackingUp(true);
    const hide = message.loading('Đang đóng gói dữ liệu sao lưu (ZIP)...', 0);
    try {
      await createBackup();
      message.success('Đã tạo bản sao lưu thành công. Đang tải về...');
      // Direct browser to download file
      window.location.href = downloadBackupUrl();
    } catch (err) {
      message.error('Lỗi tạo sao lưu: ' + (err.response?.data?.error || err.message));
    } finally {
      hide();
      setBackingUp(false);
    }
  };

  // Restore Backup
  const handleRestore = async (file) => {
    setRestoring(true);
    const hide = message.loading('Đang giải nén và phục hồi cơ sở dữ liệu...', 0);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      await restoreBackup(formData);
      message.success('🎉 Khôi phục dữ liệu thành công! Vui lòng tải lại trang.');
      fetchSettings();
    } catch (err) {
      message.error('Khôi phục dữ liệu thất bại: ' + (err.response?.data?.error || err.message));
    } finally {
      hide();
      setRestoring(false);
    }
    return false; // prevent default upload
  };

  // Services indicator status
  const getServiceStatusBadge = (status) => {
    if (status === 'running') {
      return <Badge status="processing" text={<Text type="success" style={{ fontWeight: 600 }}>ĐANG CHẠY</Text>} />;
    }
    return <Badge status="default" text={<Text type="secondary">ĐÃ DỪNG</Text>} />;
  };

  return (
    <div style={{ padding: '0 8px' }}>
      {/* Title Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0, fontWeight: 700 }}>
          ⚙️ Cấu hình hệ thống
        </Title>
        <Paragraph style={{ color: '#64748b', margin: '4px 0 0 0' }}>
          Điều chỉnh đường dẫn làm việc, tích hợp hòm thư OAuth2, sao lưu khôi phục cơ sở dữ liệu và giám sát hệ thống.
        </Paragraph>
      </div>

      <Card loading={loading} bodyStyle={{ padding: '24px 30px' }} style={{ borderRadius: '8px' }}>
        <Tabs defaultActiveKey="paths" size="large">
          
          {/* Tab 1: Paths */}
          <Tabs.TabPane
            tab={
              <span>
                <FolderOpenOutlined /> Đường dẫn
              </span>
            }
            key="paths"
          >
            <div style={{ maxWidth: 750, marginTop: 16 }}>
              <Paragraph style={{ color: '#64748b', marginBottom: 24 }}>
                Cấu hình vị trí tệp Excel nhập liệu mẫu cùng các thư mục lưu mẫu văn bản Word (.docx) dành cho Cá nhân và Tổ chức.
              </Paragraph>
              
              <Form form={pathForm} layout="vertical" onFinish={handlePathsSave}>
                <Form.Item
                  name="excel_template"
                  label="Đường dẫn file Excel mẫu"
                  rules={[{ required: true, message: 'Vui lòng nhập đường dẫn Excel mẫu' }]}
                >
                  <Input placeholder="E:\\New project\\samples\\form_nhap_lieu.xlsx" />
                </Form.Item>

                <Form.Item
                  name="individual_template_dir"
                  label="Thư mục mẫu Word (Cá nhân)"
                  rules={[{ required: true, message: 'Vui lòng nhập thư mục chứa mẫu Cá nhân' }]}
                >
                  <Input placeholder="E:\\New project\\samples\\templates\\individual" />
                </Form.Item>

                <Form.Item
                  name="organization_template_dir"
                  label="Thư mục mẫu Word (Tổ chức)"
                  rules={[{ required: true, message: 'Vui lòng nhập thư mục chứa mẫu Tổ chức' }]}
                >
                  <Input placeholder="E:\\New project\\samples\\templates\\organization" />
                </Form.Item>

                <Form.Item
                  name="output_dir"
                  label="Thư mục đầu ra (Output) - Chỉ xem"
                  tooltip="Thư mục đầu ra cố định lưu trữ các tệp xuất bản."
                >
                  <Input disabled placeholder="E:\\New project\\outputs" />
                </Form.Item>

                <Form.Item style={{ marginTop: 24 }}>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SaveOutlined />}
                    loading={savingPaths}
                  >
                    Lưu cấu hình đường dẫn
                  </Button>
                </Form.Item>
              </Form>
            </div>
          </Tabs.TabPane>

          <Tabs.TabPane
            tab={
              <span>
                <KeyOutlined /> AI API
              </span>
            }
            key="ai-api"
          >
            <div style={{ maxWidth: 650, marginTop: 16 }}>
              <Paragraph style={{ color: '#64748b', marginBottom: 24 }}>
                Gemini API key được lưu trong API.env trên máy chủ. Hệ thống chỉ hiển thị trạng thái và 4 ký tự cuối, không trả lại key về trình duyệt.
              </Paragraph>
              <Card title="Gemini API" size="small" style={{ borderRadius: '8px' }}>
                <Form form={aiForm} layout="vertical" onFinish={handleAiSave}>
                  <Form.Item label="Trạng thái">
                    {aiConfig.configured ? (
                      <Tag color="success">Đã cấu hình {aiConfig.key_suffix}</Tag>
                    ) : (
                      <Tag color="warning">Chưa cấu hình</Tag>
                    )}
                  </Form.Item>
                  <Form.Item
                    name="gemini_api_key"
                    label="Gemini API Key mới"
                    extra="Để trống nếu chỉ thay đổi model. Nhập key mới để thay key hiện tại."
                  >
                    <Input.Password autoComplete="new-password" placeholder="AIza..." />
                  </Form.Item>
                  <Form.Item
                    name="gemini_model"
                    label="Gemini model"
                    rules={[{ required: true, message: 'Vui lòng nhập Gemini model' }]}
                  >
                    <Input placeholder="gemini-2.5-flash" />
                  </Form.Item>
                  <Form.Item style={{ marginBottom: 0 }}>
                    <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={savingAi}>
                      Lưu cấu hình Gemini
                    </Button>
                  </Form.Item>
                </Form>
                <Space style={{ marginTop: 16 }} wrap>
                  <Popconfirm
                    title="Khởi động lại dịch vụ AI?"
                    description="Telegram Bot và Mail Listener sẽ tạm dừng trong vài giây để nạp API key mới."
                    onConfirm={handleAiServicesRestart}
                    okText="Khởi động lại"
                    cancelText="Hủy"
                  >
                    <Button icon={<ReloadOutlined />} loading={restartingAiServices}>
                      Áp dụng & khởi động lại dịch vụ AI
                    </Button>
                  </Popconfirm>
                  <Text type="secondary">Áp dụng cho Telegram Bot và Mail Listener.</Text>
                </Space>
              </Card>
            </div>
          </Tabs.TabPane>

          {/* Tab 2: OAuth2 Integration */}
          <Tabs.TabPane
            tab={
              <span>
                <GoogleOutlined /> Tích hợp OAuth2
              </span>
            }
            key="oauth"
          >
            <div style={{ marginTop: 16 }}>
              <Paragraph style={{ color: '#64748b', marginBottom: 24 }}>
                Cấu hình thông tin Client ID, Client Secret để thực hiện xác thực bảo mật OAuth2 với Google Gmail API và Microsoft Outlook Graph API.
              </Paragraph>

              {/* General Configuration (Redirect URI) */}
              <Card title="Cấu hình chung" size="small" style={{ borderRadius: '8px', marginBottom: 24 }}>
                <Form form={redirectForm} layout="vertical" onFinish={handleRedirectSave}>
                  <Form.Item
                    name="redirect_uri"
                    label="Redirect URI (Đường dẫn phản hồi)"
                    tooltip="Đường dẫn callback được cấu hình trong Google Cloud Console và Microsoft Azure Portal."
                    rules={[{ required: true, message: 'Vui lòng nhập Redirect URI' }]}
                  >
                    <Input placeholder="http://localhost:5173/settings" />
                  </Form.Item>
                  <Form.Item style={{ marginBottom: 0 }}>
                    <Button
                      type="primary"
                      htmlType="submit"
                      icon={<SaveOutlined />}
                      loading={savingRedirect}
                    >
                      Lưu Redirect URI
                    </Button>
                  </Form.Item>
                </Form>
              </Card>

              <Row gutter={[24, 24]}>
                {/* Google Configuration Card */}
                <Col xs={24} md={12}>
                  <Card
                    title={
                      <Space>
                        <GoogleOutlined style={{ color: '#ea4335' }} />
                        <span>Tham số Google Gmail API</span>
                      </Space>
                    }
                    size="small"
                    style={{ borderRadius: '8px', height: '100%', display: 'flex', flexDirection: 'column' }}
                    bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                  >
                    <Form form={googleForm} layout="vertical" onFinish={handleGoogleSave} style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'space-between', flex: 1 }}>
                      <div>
                        <Form.Item
                          name="client_id"
                          label="Client ID"
                          rules={[{ required: true, message: 'Vui lòng nhập Google Client ID' }]}
                        >
                          <Input placeholder="Nhập Google Client ID..." />
                        </Form.Item>

                        <Form.Item
                          name="client_secret"
                          label="Client Secret"
                          rules={[{ required: true, message: 'Vui lòng nhập Google Client Secret' }]}
                        >
                          <Input.Password placeholder="Nhập Google Client Secret..." />
                        </Form.Item>
                      </div>

                      <Form.Item style={{ marginBottom: 0, marginTop: 16 }}>
                        <Button
                          type="primary"
                          htmlType="submit"
                          icon={<SaveOutlined />}
                          loading={savingGoogle}
                          style={{ width: '100%', background: '#ea4335', borderColor: '#ea4335' }}
                        >
                          Lưu cấu hình Google
                        </Button>
                      </Form.Item>
                    </Form>
                  </Card>
                </Col>

                {/* Microsoft Configuration Card */}
                <Col xs={24} md={12}>
                  <Card
                    title={
                      <Space>
                        <WindowsOutlined style={{ color: '#0078d4' }} />
                        <span>Tham số Microsoft Outlook API</span>
                      </Space>
                    }
                    size="small"
                    style={{ borderRadius: '8px', height: '100%', display: 'flex', flexDirection: 'column' }}
                    bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                  >
                    <Form form={outlookForm} layout="vertical" onFinish={handleOutlookSave} style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'space-between', flex: 1 }}>
                      <div>
                        <Form.Item
                          name="client_id"
                          label="Client ID"
                          rules={[{ required: true, message: 'Vui lòng nhập Microsoft Client ID' }]}
                        >
                          <Input placeholder="Nhập Microsoft Client ID..." />
                        </Form.Item>

                        <Form.Item
                          name="client_secret"
                          label="Client Secret"
                          rules={[{ required: true, message: 'Vui lòng nhập Microsoft Client Secret' }]}
                        >
                          <Input.Password placeholder="Nhập Microsoft Client Secret..." />
                        </Form.Item>

                        <Form.Item
                          name="tenant"
                          label="Tenant ID"
                          tooltip="Nhập Tenant ID cụ thể hoặc 'common' cho tài khoản multi-tenant/cá nhân"
                          rules={[{ required: true, message: 'Vui lòng nhập Tenant ID' }]}
                        >
                          <Input placeholder="common" />
                        </Form.Item>

                        <Form.Item
                          name="sender_email"
                          label="Sender Email (Hòm thư gửi/nhận)"
                          tooltip="Địa chỉ email chính dùng để gửi và nhận email qua Microsoft Graph API."
                          rules={[{ required: true, type: 'email', message: 'Vui lòng nhập email hợp lệ' }]}
                        >
                          <Input placeholder="example@outlook.com" />
                        </Form.Item>
                      </div>

                      <Form.Item style={{ marginBottom: 0, marginTop: 16 }}>
                        <Button
                          type="primary"
                          htmlType="submit"
                          icon={<SaveOutlined />}
                          loading={savingOutlook}
                          style={{ width: '100%', background: '#0078d4', borderColor: '#0078d4' }}
                        >
                          Lưu cấu hình Outlook
                        </Button>
                      </Form.Item>
                    </Form>
                  </Card>
                </Col>
              </Row>

              <div style={{ marginTop: 32, borderTop: '1px solid #f0f0f0', paddingTop: 24 }}>
                <Title level={4} style={{ marginBottom: 16 }}>Trạng thái liên kết tài khoản</Title>
                <Row gutter={[24, 24]}>
                  {/* Google Workspace */}
                  <Col xs={24} md={12}>
                    <Card
                      title={
                        <Space>
                          <GoogleOutlined style={{ color: '#ea4335' }} />
                          <span>Google Gmail API</span>
                        </Space>
                      }
                      extra={
                        settings.oauth.google.connected ? (
                          <Tag color="success" style={{ fontWeight: 'bold' }}>ĐÃ LIÊN KẾT</Tag>
                        ) : (
                          <Tag color="error" style={{ fontWeight: 'bold' }}>CHƯA LIÊN KẾT</Tag>
                        )
                      }
                      bodyStyle={{ minHeight: 180, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                    >
                      <div>
                        <Paragraph style={{ color: '#64748b', fontSize: '13px' }}>
                          Sử dụng API Gmail chính thức để gửi và nhận email định giá tự động từ hòm thư Workspace hoặc Gmail cá nhân.
                        </Paragraph>
                        {settings.oauth.google.connected && (
                          <div style={{ marginTop: 8 }}>
                            <Text type="secondary">Email đang liên kết: </Text>
                            <strong>{settings.oauth.google.email}</strong>
                          </div>
                        )}
                      </div>
                      
                      <div style={{ marginTop: 16 }}>
                        {settings.oauth.google.connected ? (
                          <Popconfirm
                            title="Hủy liên kết Google?"
                            description="Xác nhận hủy liên kết hòm thư Google Gmail? Bạn sẽ không thể gửi email qua Gmail API."
                            onConfirm={() => handleOAuthDisconnect('google')}
                            okText="Hủy liên kết"
                            cancelText="Bỏ qua"
                            okButtonProps={{ danger: true }}
                          >
                            <Button danger style={{ width: '100%' }}>Hủy kết nối Google</Button>
                          </Popconfirm>
                        ) : (
                          <Button
                            type="primary"
                            icon={<GoogleOutlined />}
                            onClick={() => handleOAuthConnect('google')}
                            style={{ width: '100%', background: '#ea4335', borderColor: '#ea4335' }}
                          >
                            Kết nối Google Workspace
                          </Button>
                        )}
                      </div>
                    </Card>
                  </Col>

                  {/* Microsoft Outlook */}
                  <Col xs={24} md={12}>
                    <Card
                      title={
                        <Space>
                          <WindowsOutlined style={{ color: '#0078d4' }} />
                          <span>Microsoft Outlook Graph API</span>
                        </Space>
                      }
                      extra={
                        settings.oauth.outlook.connected ? (
                          <Tag color="success" style={{ fontWeight: 'bold' }}>ĐÃ LIÊN KẾT</Tag>
                        ) : (
                          <Tag color="error" style={{ fontWeight: 'bold' }}>CHƯA LIÊN KẾT</Tag>
                        )
                      }
                      bodyStyle={{ minHeight: 180, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                    >
                      <div>
                        <Paragraph style={{ color: '#64748b', fontSize: '13px' }}>
                          Sử dụng Microsoft Graph API để gửi nhận email từ hòm thư Office 365, Outlook.com hoặc Hotmail doanh nghiệp.
                        </Paragraph>
                        {settings.oauth.outlook.connected && (
                          <div style={{ marginTop: 8 }}>
                            <Text type="secondary">Email đang liên kết: </Text>
                            <strong>{settings.oauth.outlook.email}</strong>
                          </div>
                        )}
                      </div>

                      <div style={{ marginTop: 16 }}>
                        {settings.oauth.outlook.connected ? (
                          <Popconfirm
                            title="Hủy liên kết Microsoft?"
                            description="Xác nhận hủy liên kết hòm thư Microsoft Outlook?"
                            onConfirm={() => handleOAuthDisconnect('outlook')}
                            okText="Hủy liên kết"
                            cancelText="Bỏ qua"
                            okButtonProps={{ danger: true }}
                          >
                            <Button danger style={{ width: '100%' }}>Hủy kết nối Outlook</Button>
                          </Popconfirm>
                        ) : (
                          <Button
                            type="primary"
                            icon={<WindowsOutlined />}
                            onClick={() => handleOAuthConnect('outlook')}
                            style={{ width: '100%', background: '#0078d4', borderColor: '#0078d4' }}
                          >
                            Kết nối Microsoft Outlook
                          </Button>
                        )}
                      </div>
                    </Card>
                  </Col>
                </Row>
              </div>

              <div style={{ marginTop: 32, borderTop: '1px solid #f0f0f0', paddingTop: 24 }}>
                <Title level={4} style={{ marginBottom: 4 }}>Mail Sơ bộ</Title>
                <Paragraph style={{ color: '#64748b', marginBottom: 12 }}>
                  Cấu hình này chỉ áp dụng cho mail Sơ bộ gửi từ Telegram bot. Luồng gửi hồ sơ bình thường vẫn dùng cấu hình OAuth2 chung bên trên.
                </Paragraph>
                <Paragraph style={{ color: '#64748b', fontSize: '13px', marginBottom: 16 }}>
                  {settings.oauth.google.connected ? 'Google đã liên kết' : 'Google chưa liên kết'} | {settings.oauth.outlook.connected ? 'Outlook đã liên kết' : 'Outlook chưa liên kết'}
                </Paragraph>

                <Card size="small" style={{ borderRadius: '8px', maxWidth: 650 }}>
                  <Form form={soboForm} layout="vertical" onFinish={handleSoboSave}>
                    <Form.Item
                      name="provider"
                      label="Nhà cung cấp gửi mail Sơ bộ"
                      rules={[{ required: true }]}
                    >
                      <Select placeholder="Chọn nhà cung cấp...">
                        <Select.Option value="google">Google Gmail API</Select.Option>
                        <Select.Option value="outlook">Microsoft Outlook</Select.Option>
                      </Select>
                    </Form.Item>

                    <Form.Item
                      name="mail_username"
                      label="Tài khoản gửi mail Sơ bộ"
                      rules={[{ required: true, message: 'Vui lòng nhập tài khoản gửi' }]}
                    >
                      <Input placeholder="hostktpro@gmail.com" />
                    </Form.Item>

                    <Form.Item
                      name="mail_from"
                      label="From hiển thị cho mail Sơ bộ"
                      rules={[{ required: true, message: 'Vui lòng nhập địa chỉ gửi hiển thị' }]}
                    >
                      <Input placeholder="hostktpro@gmail.com" />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 0 }}>
                      <Button
                        type="primary"
                        htmlType="submit"
                        icon={<SaveOutlined />}
                        loading={savingSobo}
                      >
                        Lưu cấu hình mail Sơ bộ
                      </Button>
                    </Form.Item>
                  </Form>
                </Card>
              </div>
            </div>
          </Tabs.TabPane>

          {/* Tab 3: Backup & Restore */}
          <Tabs.TabPane
            tab={
              <span>
                <CloudUploadOutlined /> Sao lưu & Phục hồi
              </span>
            }
            key="backup"
          >
            <div style={{ marginTop: 16, maxWidth: 650 }}>
              <Paragraph style={{ color: '#64748b', marginBottom: 24 }}>
                Quản lý các điểm phục hồi dữ liệu hệ thống. Sao lưu sẽ nén tất cả các file SQLite cơ sở dữ liệu cùng tệp cấu hình tham số hệ thống thành một tệp ZIP.
              </Paragraph>
              
              <Card title="Tạo bản sao lưu dữ liệu" size="small" style={{ marginBottom: 24 }}>
                <Paragraph style={{ fontSize: '13px', color: '#64748b' }}>
                  Hệ thống tự động lưu giữ tối đa 10 phiên bản sao lưu gần nhất. Nhấp nút bên dưới để tạo và tải về bản sao lưu ZIP của hôm nay.
                </Paragraph>
                <Button
                  type="primary"
                  icon={<CloudDownloadOutlined />}
                  onClick={handleBackup}
                  loading={backingUp}
                >
                  Tạo & Tải bản sao lưu (ZIP)
                </Button>
              </Card>

              <Card title="Khôi phục dữ liệu từ file sao lưu" size="small">
                <Paragraph style={{ fontSize: '13px', color: '#64748b' }}>
                  ⚠️ <strong>Cảnh báo nguy hiểm:</strong> Quá trình khôi phục sẽ ghi đè toàn bộ dữ liệu hồ sơ và cài đặt hiện tại bằng thông tin trong file ZIP. Hành động này không thể hoàn tác.
                </Paragraph>
                <Upload
                  accept=".zip"
                  beforeUpload={handleRestore}
                  showUploadList={false}
                  disabled={restoring}
                >
                  <Button
                    danger
                    type="primary"
                    icon={<CloudUploadOutlined />}
                    loading={restoring}
                  >
                    Chọn file ZIP để khôi phục
                  </Button>
                </Upload>
              </Card>
            </div>
          </Tabs.TabPane>

          {/* Tab 4: System Details */}
          <Tabs.TabPane
            tab={
              <span>
                <SlidersOutlined /> Hệ thống
              </span>
            }
            key="system"
          >
            <div style={{ marginTop: 16 }}>
              <Paragraph style={{ color: '#64748b', marginBottom: 24 }}>
                Thông số phiên bản, kích thước cơ sở dữ liệu hồ sơ và giám sát các dịch vụ ngầm (background processes).
              </Paragraph>
              
              <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col span={12} sm={8}>
                  <Card size="small" bordered>
                    <Statistic title="Phiên bản hệ thống" value={settings.system.version} prefix={<SlidersOutlined />} />
                  </Card>
                </Col>
                <Col span={12} sm={8}>
                  <Card size="small" bordered>
                    <Statistic title="Kích thước Cơ sở dữ liệu" value={settings.system.db_size} prefix={<DatabaseOutlined />} />
                  </Card>
                </Col>
              </Row>

              <Card title="Trạng thái dịch vụ chạy nền (Services)" size="small">
                <Descriptions bordered column={1} size="small">
                  <Descriptions.Item label="Telegram Bot Server">
                    {getServiceStatusBadge(settings.services.telegram)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Mail Listener Service (Hòm thư)">
                    {getServiceStatusBadge(settings.services.mail_listener)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Ngrok Tunnel Service (Đường truyền)">
                    {getServiceStatusBadge(settings.services.ngrok)}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </div>
          </Tabs.TabPane>

        </Tabs>
      </Card>
    </div>
  );
}
