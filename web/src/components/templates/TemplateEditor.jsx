import React, { useState, useEffect } from 'react';
import { Drawer, Descriptions, Tag, Upload, Timeline, Space, Spin, Empty, Button, Form, Input, message, Card } from 'antd';
import { UploadOutlined, HistoryOutlined, FileTextOutlined, TagsOutlined } from '@ant-design/icons';
import { getTemplateDetail, uploadTemplateVersion, getTemplateHistory } from '../../api/templates';
import { useAuth } from '../../hooks/useAuth';

export default function TemplateEditor({ open, templateName, onClose, onSuccess }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [form] = Form.useForm();

  const fetchDetail = async (name) => {
    setLoading(true);
    try {
      const res = await getTemplateDetail(name);
      setDetail(res.data);
    } catch (err) {
      console.error(err);
      message.error('Không thể tải chi tiết mẫu thiết kế');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async (name) => {
    setLoadingHistory(true);
    try {
      const res = await getTemplateHistory(name);
      setHistory(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (open && templateName) {
      fetchDetail(templateName);
      fetchHistory(templateName);
      form.resetFields();
    } else {
      setDetail(null);
      setHistory([]);
    }
  }, [open, templateName]);

  const handleUpload = async (file) => {
    try {
      const values = await form.validateFields();
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('editor_name', user?.username || 'Admin');
      formData.append('description', values.description || 'Cập nhật phiên bản qua web client');

      await uploadTemplateVersion(templateName, formData);
      message.success('Cập nhật phiên bản mới thành công!');
      form.resetFields();
      fetchDetail(templateName);
      fetchHistory(templateName);
      if (onSuccess) onSuccess();
    } catch (err) {
      if (err.name !== 'ValidationError') {
        message.error('Lỗi tải tệp lên: ' + (err.response?.data?.error || err.message));
      }
    } finally {
      setUploading(false);
    }
    return false; // prevent default upload
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '-';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleString('vi-VN');
    } catch {
      return isoStr;
    }
  };

  return (
    <Drawer
      title={
        <Space>
          <FileTextOutlined style={{ color: '#007f7a' }} />
          <span>Chi tiết Mẫu: {templateName}</span>
        </Space>
      }
      placement="right"
      width={650}
      onClose={onClose}
      open={open}
      destroyOnClose
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px 0' }}>
          <Spin size="large" tip="Đang tải thông tin mẫu..." />
        </div>
      ) : detail ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* File General Descriptions */}
          <Descriptions title="Thông tin chung" bordered column={1} size="small">
            <Descriptions.Item label="Tên mẫu">
              <strong>{detail.name}</strong>
            </Descriptions.Item>
            <Descriptions.Item label="Đường dẫn mẫu">
              <span style={{ fontSize: '12px', wordBreak: 'break-all' }}>{detail.path}</span>
            </Descriptions.Item>
            <Descriptions.Item label="Kích thước">
              {(detail.size / 1024).toFixed(1)} KB
            </Descriptions.Item>
            <Descriptions.Item label="Cập nhật lần cuối">
              {formatDate(detail.last_modified)}
            </Descriptions.Item>
          </Descriptions>

          {/* Placeholders Tags List */}
          <div>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'rgba(0, 0, 0, 0.88)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
              <TagsOutlined /> Danh sách thẻ giữ chỗ (Placeholders)
            </h3>
            {detail.placeholders && detail.placeholders.length > 0 ? (
              <div style={{ display: 'flex', wrap: 'wrap', gap: '8px 4px', flexWrap: 'wrap' }}>
                {detail.placeholders.map((p) => (
                  <Tag color="blue" key={p} style={{ margin: '2px 0' }}>
                    {`{{${p}}}`}
                  </Tag>
                ))}
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Không phát hiện thẻ giữ chỗ nào trong mẫu" />
            )}
          </div>

          {/* Preview Text Snippet */}
          <div>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'rgba(0, 0, 0, 0.88)', marginBottom: 12 }}>
              📄 Xem trước nội dung mẫu
            </h3>
            <div style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              padding: '12px 16px',
              maxHeight: '150px',
              overflowY: 'auto',
              fontSize: '13px',
              lineHeight: '1.6',
              whiteSpace: 'pre-wrap',
              color: '#475569'
            }}>
              {detail.content_preview || <span style={{ color: '#94a3b8' }}>(Mẫu trống hoặc không chứa ký tự văn bản)</span>}
            </div>
          </div>

          {/* Upload Area for New Version */}
          <Card title="Tải lên phiên bản mới" size="small" style={{ border: '1px solid #cbd5e1' }}>
            <Form form={form} layout="vertical">
              <Form.Item
                name="description"
                label="Ghi chú thay đổi (Lý do cập nhật)"
                rules={[{ required: true, message: 'Vui lòng nhập lý do cập nhật phiên bản mới.' }]}
              >
                <Input placeholder="Ví dụ: Cập nhật điều khoản phí dịch vụ hoặc địa chỉ mẫu..." />
              </Form.Item>
              <Form.Item label="Chọn file (.docx) thay thế">
                <Upload
                  accept=".docx"
                  beforeUpload={handleUpload}
                  showUploadList={false}
                  disabled={uploading}
                >
                  <Button type="primary" icon={<UploadOutlined />} loading={uploading}>
                    {uploading ? 'Đang cập nhật...' : 'Chọn file Word thay thế'}
                  </Button>
                </Upload>
              </Form.Item>
            </Form>
          </Card>

          {/* Version History Timeline */}
          <div>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'rgba(0, 0, 0, 0.88)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <HistoryOutlined /> Lịch sử phiên bản mẫu
            </h3>
            {loadingHistory ? (
              <div style={{ textAlign: 'center', padding: '20px 0' }}><Spin size="small" /></div>
            ) : history.length > 0 ? (
              <Timeline style={{ paddingLeft: 12, marginTop: 12 }}>
                {history.map((h) => (
                  <Timeline.Item key={h.version} color={h.action === 'upload_version' ? 'blue' : 'gray'}>
                    <div style={{ fontWeight: 600, color: '#1e293b' }}>
                      Phiên bản {h.version} - {formatDate(h.modified_at)}
                    </div>
                    <div style={{ fontSize: '12px', color: '#64748b', marginTop: 4 }}>
                      Người cập nhật: <strong>{h.modified_by}</strong>
                    </div>
                    {h.details?.description && (
                      <div style={{
                        fontSize: '13px',
                        color: '#334155',
                        background: '#f1f5f9',
                        padding: '6px 12px',
                        borderRadius: '4px',
                        marginTop: 4,
                        display: 'inline-block'
                      }}>
                        📝 {h.details.description}
                      </div>
                    )}
                  </Timeline.Item>
                ))}
              </Timeline>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Chưa có lịch sử cập nhật phiên bản" />
            )}
          </div>
        </div>
      ) : (
        <Empty description="Không có dữ liệu mẫu" />
      )}
    </Drawer>
  );
}
