import React, { useState, useEffect } from 'react';
import { Button, List, Space, Card, Tag, Radio, message, Tooltip, Empty, Spin } from 'antd';
import { 
  FileWordOutlined, 
  FilePdfOutlined, 
  FileZipOutlined, 
  FileOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  MailOutlined,
  SendOutlined,
  EyeOutlined
} from '@ant-design/icons';
import { listDocuments, generateDocuments, downloadDocument, downloadAllZip } from '../../api/documents';
import DocumentPreview from './DocumentPreview';
import SendEmailModal from './SendEmailModal';
import DeliveryModal from './DeliveryModal';

export default function CaseDocuments({ caseData, onCaseRefresh }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [downloadingZip, setDownloadingZip] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState('standard'); // 'standard' | 'advance'
  
  // Modals state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState('');
  const [emailOpen, setEmailOpen] = useState(false);
  const [deliveryOpen, setDeliveryOpen] = useState(false);

  const caseId = caseData?.id;
  const isOrganization = caseData?.customer_type === 'organization';

  useEffect(() => {
    if (caseId) {
      fetchDocuments();
    }
  }, [caseId]);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const res = await listDocuments(caseId);
      setDocuments(res.data || []);
    } catch (err) {
      console.error(err);
      message.error('Không thể lấy danh sách tài liệu');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      message.loading({ content: 'Đang tạo bộ văn bản...', key: 'gen' });
      await generateDocuments(caseId, paymentMethod);
      message.success({ content: 'Tạo văn bản thành công! 🎉', key: 'gen' });
      fetchDocuments();
      if (onCaseRefresh) onCaseRefresh();
    } catch (err) {
      console.error(err);
      message.error({ content: err.response?.data?.error || 'Tạo văn bản thất bại', key: 'gen' });
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (filename) => {
    try {
      const response = await downloadDocument(caseId, filename);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error(err);
      message.error('Tải tài liệu thất bại');
    }
  };

  const handleDownloadZip = async () => {
    setDownloadingZip(true);
    try {
      message.loading({ content: 'Đang đóng gói ZIP...', key: 'zip' });
      const response = await downloadAllZip(caseId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Ho_so_Case_${caseId}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success({ content: 'Tải ZIP thành công!', key: 'zip' });
    } catch (err) {
      console.error(err);
      message.error({ content: 'Tải ZIP thất bại', key: 'zip' });
    } finally {
      setDownloadingZip(false);
    }
  };

  const getFileIcon = (type) => {
    switch (type) {
      case 'docx':
      case 'doc':
        return <FileWordOutlined style={{ fontSize: 24, color: '#0f6cbd' }} />;
      case 'pdf':
        return <FilePdfOutlined style={{ fontSize: 24, color: '#ef4444' }} />;
      case 'zip':
      case 'rar':
        return <FileZipOutlined style={{ fontSize: 24, color: '#eab308' }} />;
      default:
        return <FileOutlined style={{ fontSize: 24, color: '#6b7280' }} />;
    }
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString('vi-VN');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Top Action Control Panel */}
      <Card style={{ borderRadius: 10, border: '1px solid #e5e7eb' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <Space size="middle" wrap>
            {isOrganization && (
              <div style={{ marginRight: 8 }}>
                <span style={{ marginRight: 8, fontWeight: 500 }}>Hợp đồng tổ chức:</span>
                <Radio.Group onChange={(e) => setPaymentMethod(e.target.value)} value={paymentMethod}>
                  <Radio value="standard">Không tạm ứng</Radio>
                  <Radio value="advance">Có tạm ứng</Radio>
                </Radio.Group>
              </div>
            )}
            
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleGenerate}
              loading={generating}
              style={{ borderRadius: 6 }}
            >
              Tạo bộ văn bản
            </Button>

            {documents.length > 0 && (
              <Button
                icon={<DownloadOutlined />}
                onClick={handleDownloadZip}
                loading={downloadingZip}
                style={{ borderRadius: 6 }}
              >
                Tải trọn bộ ZIP
              </Button>
            )}
          </Space>

          <Space size="middle" wrap>
            <Button
              icon={<MailOutlined style={{ color: '#0f6cbd' }} />}
              onClick={() => setEmailOpen(true)}
              style={{ borderRadius: 6 }}
            >
              Gửi mail yêu cầu
            </Button>
            <Button
              type="primary"
              ghost
              icon={<SendOutlined />}
              onClick={() => setDeliveryOpen(true)}
              style={{ borderRadius: 6 }}
            >
              Phát hành chứng thư
            </Button>
          </Space>
        </div>
      </Card>

      {/* Documents List */}
      <Card 
        title="Danh sách tài liệu đã tạo"
        styles={{ body: { padding: '8px 24px' } }}
        style={{ borderRadius: 10, border: '1px solid #e5e7eb' }}
      >
        <Spin spinning={loading}>
          {documents.length === 0 ? (
            <Empty 
              image={Empty.PRESENTED_IMAGE_SIMPLE} 
              description="Chưa có tài liệu nào được tạo cho hồ sơ này."
              style={{ padding: '24px 0' }}
            />
          ) : (
            <List
              itemLayout="horizontal"
              dataSource={documents}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    item.type === 'docx' && (
                      <Button
                        type="link"
                        icon={<EyeOutlined />}
                        onClick={() => { setPreviewFile(item.name); setPreviewOpen(true); }}
                      >
                        Xem trước
                      </Button>
                    ),
                    <Button
                      type="link"
                      icon={<DownloadOutlined />}
                      onClick={() => handleDownload(item.name)}
                    >
                      Tải về
                    </Button>
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    avatar={getFileIcon(item.type)}
                    title={<strong>{item.name}</strong>}
                    description={
                      <Space size="large">
                        <span>Dung lượng: {formatSize(item.size)}</span>
                        <span>Đã tạo: {formatDate(item.created_at)}</span>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Card>

      {/* Preview Drawer */}
      <DocumentPreview 
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        caseId={caseId}
        filename={previewFile}
      />

      {/* Send Email Modal */}
      <SendEmailModal
        open={emailOpen}
        onClose={() => setEmailOpen(false)}
        caseId={caseId}
        documents={documents.filter(d => d.type === 'docx' || d.type === 'pdf')}
        initialSubject={`Century Valuation - Kết quả thẩm định hồ sơ ${caseData?.contract_number || ''}`}
      />

      {/* Delivery / Certificate Issuance Modal */}
      <DeliveryModal
        open={deliveryOpen}
        onClose={() => setDeliveryOpen(false)}
        caseId={caseId}
        onSuccess={() => {
          fetchDocuments();
          if (onCaseRefresh) onCaseRefresh();
        }}
      />
    </div>
  );
}
