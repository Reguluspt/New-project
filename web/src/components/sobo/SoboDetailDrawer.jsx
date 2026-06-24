import React, { useState, useEffect } from 'react';
import { Drawer, Descriptions, Tag, Button, List, Space, Empty, Spin, message } from 'antd';
import { DownloadOutlined, CompassOutlined, FilePdfOutlined, ContainerOutlined } from '@ant-design/icons';
import { getSoboFiles } from '../../api/sobo';

export default function SoboDetailDrawer({ open, record, onClose }) {
  const [files, setFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);

  useEffect(() => {
    if (open && record) {
      setLoadingFiles(true);
      getSoboFiles(record.id)
        .then((res) => {
          setFiles(res.data);
        })
        .catch((err) => {
          console.error(err);
          message.error('Không thể tải danh sách GCN đính kèm');
        })
        .finally(() => {
          setLoadingFiles(false);
        });
    } else {
      setFiles([]);
    }
  }, [open, record]);

  if (!record) return null;

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

  const formatDuration = (sentAt, respAt, rawStatus) => {
    const start = sentAt ? new Date(sentAt) : null;
    const end = rawStatus === 'RESPONDED' && respAt ? new Date(respAt) : new Date();
    if (!start) return '-';

    const diffMs = end - start;
    if (diffMs < 0) return '0g';
    const totalHours = Math.floor(diffMs / 3600000);
    const days = Math.floor(totalHours / 24);
    const hours = totalHours % 24;

    if (days > 0) {
      return `${days} ngày ${hours}g`;
    }
    return `${hours}g`;
  };

  const isPending = record.status === 'PENDING';
  const elapsed = formatDuration(record.outbound_sent_at || record.created_at, record.responded_at, record.status);

  return (
    <Drawer
      title={
        <Space>
          <ContainerOutlined style={{ color: '#0f6cbd' }} />
          <span>Chi tiết Yêu cầu Sơ bộ #{record.id}</span>
        </Space>
      }
      placement="right"
      width={600}
      onClose={onClose}
      open={open}
      destroyOnClose
    >
      <Descriptions title="Thông tin chung" bordered column={1} size="small" style={{ marginBottom: 24 }}>
        <Descriptions.Item label="Mã hồ sơ">
          <strong>#{record.id}</strong>
        </Descriptions.Item>
        
        <Descriptions.Item label="Trạng thái">
          {record.status === 'RESPONDED' ? (
            <Tag color="success" style={{ fontWeight: 'bold' }}>🟢 ĐÃ PHẢN HỒI</Tag>
          ) : (
            <Tag color="error" style={{ fontWeight: 'bold' }}>🔴 CHỜ PHẢN HỒI</Tag>
          )}
        </Descriptions.Item>

        <Descriptions.Item label="Ngày tạo/Ngày gửi">
          {formatDate(record.outbound_sent_at || record.created_at)}
        </Descriptions.Item>

        <Descriptions.Item label="Thời gian xử lý">
          {isPending ? (
            <span style={{ color: '#ef4444', fontWeight: 600 }}>⌛ {elapsed} (đang chờ)</span>
          ) : (
            <span style={{ color: '#10b981', fontWeight: 600 }}>⚡ {elapsed} (phản hồi xong)</span>
          )}
        </Descriptions.Item>

        {record.responded_at && (
          <Descriptions.Item label="Ngày phản hồi">
            {formatDate(record.responded_at)}
          </Descriptions.Item>
        )}

        <Descriptions.Item label="Nguồn khách/Đối tác">
          {record.source || '-'}
        </Descriptions.Item>

        <Descriptions.Item label="Email người nhận">
          <code>{record.email_recipient || '-'}</code>
        </Descriptions.Item>
      </Descriptions>

      <Descriptions title="Chi tiết Tài sản" bordered column={1} size="small" style={{ marginBottom: 24 }}>
        <Descriptions.Item label="Loại tài sản">
          {record.asset_type === 'machinery' ? '⚙️ Máy móc thiết bị' : '🏠 Bất động sản'}
        </Descriptions.Item>

        {record.asset_type === 'machinery' ? (
          <Descriptions.Item label="Tên thiết bị">
            {record.equipment_name || '-'}
          </Descriptions.Item>
        ) : (
          <>
            <Descriptions.Item label="Số thửa / Số tờ">
              {record.so_thua ? `Thửa số ${record.so_thua}` : ''}
              {record.so_thua && record.so_to ? ' - ' : ''}
              {record.so_to ? `Tờ bản đồ ${record.so_to}` : ''}
              {!record.so_thua && !record.so_to ? '-' : ''}
            </Descriptions.Item>
            <Descriptions.Item label="Địa chỉ thửa đất">
              {record.dia_chi || '-'}
            </Descriptions.Item>
          </>
        )}

        {record.link && (
          <Descriptions.Item label="Bản đồ / Location">
            <Button
              type="link"
              icon={<CompassOutlined />}
              href={record.link}
              target="_blank"
              style={{ padding: 0 }}
            >
              Mở Google Maps
            </Button>
          </Descriptions.Item>
        )}

        <Descriptions.Item label="Ghi chú nội bộ">
          <span style={{ whiteSpace: 'pre-wrap' }}>{record.note || '-'}</span>
        </Descriptions.Item>
      </Descriptions>

      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'rgba(0, 0, 0, 0.88)' }}>
            📁 Tệp đính kèm (GCN)
          </h3>
          {files.length > 1 && (
            <Button
              type="primary"
              size="small"
              icon={<DownloadOutlined />}
              href={`/api/sobo/${record.id}/files/download-all`}
              target="_blank"
            >
              Tải tất cả (ZIP)
            </Button>
          )}
        </div>

        {loadingFiles ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin tip="Đang tải danh sách tệp..." />
          </div>
        ) : files.length > 0 ? (
          <List
            size="small"
            bordered
            dataSource={files}
            renderItem={(file) => (
              <List.Item
                actions={[
                  <Button
                    type="link"
                    size="small"
                    icon={<DownloadOutlined />}
                    href={file.url}
                    target="_blank"
                  >
                    Tải về
                  </Button>
                ]}
              >
                <List.Item.Meta
                  avatar={<FilePdfOutlined style={{ fontSize: '20px', color: '#ff4d4f' }} />}
                  title={file.filename}
                  description={`${(file.size / 1024).toFixed(1)} KB`}
                />
              </List.Item>
            )}
          />
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Không có tệp đính kèm nào khả dụng hoặc không tồn tại trên ổ đĩa" />
        )}
      </div>

      <Descriptions title="Đối soát email" bordered column={1} size="small">
        <Descriptions.Item label="Tiêu đề email gửi">
          <span style={{ fontSize: '12px' }}>{record.outbound_subject || '-'}</span>
        </Descriptions.Item>
        <Descriptions.Item label="Message ID">
          <code style={{ fontSize: '11px', wordBreak: 'break-all' }}>{record.outbound_message_id || '-'}</code>
        </Descriptions.Item>
      </Descriptions>
    </Drawer>
  );
}
