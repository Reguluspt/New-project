import React, { useState } from 'react';
import { Table, Button, Popconfirm, Tooltip, Modal } from 'antd';
import {
  EyeOutlined,
  DeleteOutlined,
  CompassOutlined,
  DownloadOutlined,
  MailOutlined,
  ImportOutlined,
  StopOutlined
} from '@ant-design/icons';
import { useResizableColumns } from '../../hooks/useResizableColumns';

// Check if a string contains HTML tags
const isHtmlContent = (str) => /<[a-z][\s\S]*>/i.test(str || '');

// Inline styles injected inside the modal shadow DOM to format email HTML tables/images
const EMAIL_HTML_STYLES = `
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; color: #374151; margin: 0; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  th, td { border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; font-size: 12px; }
  th { background: #f3f4f6; font-weight: 600; color: #111827; }
  tr:nth-child(even) td { background: #f9fafb; }
  img { max-width: 100%; height: auto; border-radius: 4px; margin: 4px 0; }
  p { margin: 4px 0; line-height: 1.6; }
  a { color: #2563eb; }
  ul, ol { margin: 4px 0; padding-left: 20px; }
`;

export default function SoboTable({
  loading,
  dataSource,
  pagination,
  onChange,
  onView,
  onEdit,
  onDelete,
  isGuest,
  onConvert,
  onUnfollow
}) {
  const [previewRecord, setPreviewRecord] = useState(null);

  const { getResizableProps } = useResizableColumns('sobo_list', {
    id_date: 120,
    info: 450,
    response_content: 360,
    status_time: 130,
    actions: 260
  });

  const getAssetDisplay = (record) => {
    if (record.asset_type === 'machinery') {
      return (
        <span>
          ⚙️ Thử: {record.equipment_name || '-'}
        </span>
      );
    }
    const parts = [];
    if (record.so_thua) parts.push(`Thửa: ${record.so_thua}`);
    if (record.so_to) parts.push(`Tờ: ${record.so_to}`);
    const prefix = parts.join(', ');
    const addr = record.dia_chi || '';
    if (prefix && addr) {
      return `${prefix}; ${addr}`;
    }
    return `${addr || prefix || '-'}`;
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '-';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return isoStr;
      return d.toLocaleDateString('vi-VN') + ' ' + d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
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

  const columns = [
    {
      title: (
        <span className="sobo-compact-header">
          MÃ HỒ SƠ /<br />NGÀY GỬI
        </span>
      ),
      key: 'id_date',
      width: 120,
      render: (_, record) => (
        <div className="sobo-id-date-cell">
          <div style={{ fontSize: '15px', fontWeight: 800, color: '#0f172a' }}>
            #{record.id}
          </div>
          <div style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>
            {formatDate(record.outbound_sent_at || record.created_at)}
          </div>
        </div>
      )
    },
    {
      title: 'THÔNG TIN HỒ SƠ',
      key: 'info',
      render: (_, record) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ fontSize: '13px', fontWeight: 400, color: '#0f172a', lineHeight: 1.4 }}>
            {record.outbound_subject || '-'}
          </div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a', lineHeight: 1.4 }}>
            🏡 {getAssetDisplay(record)}
          </div>
          <div style={{ fontSize: '13px', color: '#475569', lineHeight: 1.4 }}>
            <span style={{ fontWeight: 600, color: '#0f172a' }}>{record.source || '-'}</span>
            <span style={{ margin: '0 8px', color: '#cbd5e1' }}>|</span>
            <span>{record.email_recipient || '-'}</span>
          </div>
        </div>
      )
    },
    {
      title: 'MAIL PHẢN HỒI',
      key: 'response_content',
      width: 250,
      render: (_, record) => {
        const content = record.response_content;
        if (!content || !content.trim()) {
          return (
            <span style={{ color: '#cbd5e1', fontStyle: 'italic', fontSize: '12px' }}>
              Chưa có phản hồi
            </span>
          );
        }

        const isHtml = isHtmlContent(content);

        return (
          <div
            onClick={(e) => { e.stopPropagation(); setPreviewRecord(record); }}
            style={{ cursor: 'pointer', maxWidth: '100%', minWidth: 0, overflow: 'hidden' }}
          >
            {/* Rút gọn với fade-out */}
            <div className="sobo-response-preview" style={{
              position: 'relative',
              maxHeight: '110px',
              overflow: 'hidden',
              fontSize: '12px',
              color: '#374151',
              lineHeight: 1.5,
              maxWidth: '100%',
              minWidth: 0,
            }}>
              {isHtml ? (
                <div
                  dangerouslySetInnerHTML={{ __html: content }}
                  style={{ pointerEvents: 'none' }}
                />
              ) : (
                <div style={{ whiteSpace: 'pre-wrap' }}>{content}</div>
              )}
              {/* Fade overlay */}
              <div style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                height: '40px',
                background: 'linear-gradient(transparent, rgba(255,255,255,0.95))',
                pointerEvents: 'none'
              }} />
            </div>
            {/* "Xem chi tiết" link */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              marginTop: '4px',
              color: '#2563eb',
              fontSize: '11px',
              fontWeight: 600,
            }}>
              <MailOutlined style={{ fontSize: '11px' }} />
              Xem chi tiết
            </div>
          </div>
        );
      }
    },
    {
      title: (
        <span className="sobo-compact-header">
          TRẠNG THÁI /<br />THỜI GIAN
        </span>
      ),
      key: 'status_time',
      width: 130,
      align: 'center',
      render: (_, record) => {
        const elapsed = formatDuration(record.outbound_sent_at || record.created_at, record.responded_at, record.status);
        const isResponded = record.status === 'RESPONDED';
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center' }}>
            <div>
              {isResponded ? (
                <span className="sobo-status-pill" style={{ 
                  display: 'inline-flex', 
                  alignItems: 'center', 
                  background: '#ecfdf5', 
                  color: '#047857', 
                  border: '1px solid #d1fae5',
                  padding: '4px 8px', 
                  borderRadius: '16px', 
                  fontWeight: 700, 
                  fontSize: '11px' 
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#047857', marginRight: 6 }} />
                  Đã phản hồi
                </span>
              ) : (
                <span className="sobo-status-pill" style={{ 
                  display: 'inline-flex', 
                  alignItems: 'center', 
                  background: '#fef2f2', 
                  color: '#b91c1c', 
                  border: '1px solid #fee2e2',
                  padding: '4px 8px', 
                  borderRadius: '16px', 
                  fontWeight: 700, 
                  fontSize: '11px' 
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#c2413d', marginRight: 6 }} />
                  Chờ phản hồi
                </span>
              )}
            </div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              fontSize: '12px', 
              fontWeight: 600, 
              color: '#475569'
            }}>
              <span style={{ 
                width: 6, 
                height: 6, 
                borderRadius: '50%', 
                background: isResponded ? '#047857' : '#c2413d', 
                marginRight: 6 
              }} />
              {isResponded ? 'Xử lý: ' : 'Trễ: '}{elapsed}
            </div>
          </div>
        );
      }
    },
    {
      title: 'THAO TÁC',
      key: 'actions',
    width: 220,
      align: 'center',
      render: (_, record) => (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }} onClick={(e) => e.stopPropagation()}>
          <Tooltip title="Mở bản đồ">
            <Button
              type="text"
              disabled={!record.link}
              href={record.link || undefined}
              target="_blank"
              icon={<CompassOutlined style={{ color: record.link ? '#007f7a' : '#bfbfbf', fontSize: '18px' }} />}
              style={{ 
                width: '36px', 
                height: '36px', 
                minWidth: '36px', 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center', 
                borderRadius: '6px', 
                backgroundColor: record.link ? '#f1f5f9' : '#fafafa', 
                border: 'none', 
                padding: 0 
              }}
            />
          </Tooltip>
          <Tooltip title="Tải GCN">
            <Button
              type="text"
              disabled={!record.attachment_paths || record.attachment_paths.trim() === ''}
              href={record.attachment_paths ? `/api/sobo/${record.id}/files/download-all` : undefined}
              target="_blank"
              icon={<DownloadOutlined style={{ color: (record.attachment_paths && record.attachment_paths.trim() !== '') ? '#007f7a' : '#bfbfbf', fontSize: '18px' }} />}
              style={{ 
                width: '36px', 
                height: '36px', 
                minWidth: '36px', 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center', 
                borderRadius: '6px', 
                backgroundColor: (record.attachment_paths && record.attachment_paths.trim() !== '') ? '#f1f5f9' : '#fafafa', 
                border: 'none', 
                padding: 0 
              }}
            />
          </Tooltip>
 {!isGuest && (
            <Tooltip title="Chuyển Sang Thẩm Định">
              <Button
                type="text"
                icon={<ImportOutlined style={{ color: '#7c3aed', fontSize: '18px' }} />}
                onClick={() => onConvert(record)}
                style={{
                  width: '36px',
                  height: '36px',
                  minWidth: '36px',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  borderRadius: '6px',
                  backgroundColor: '#f5f3ff',
                  border: 'none',
                  padding: 0
                }}
              />
            </Tooltip>
          )}
          {!isGuest && (
            <Tooltip title="Bỏ theo dõi">
              <Popconfirm
                title="Bỏ theo dõi mail phản hồi"
                description="Hồ sơ này sẽ không còn hiển thị trong danh sách chờ phản hồi."
                onConfirm={() => onUnfollow(record.id)}
                okText="Bỏ theo dõi"
                cancelText="Hủy"
              >
                <Button
                  type="text"
                  icon={<StopOutlined style={{ color: '#d97706', fontSize: '18px' }} />}
                  style={{
                    width: '36px',
                    height: '36px',
                    minWidth: '36px',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    borderRadius: '6px',
                    backgroundColor: '#fffbeb',
                    border: 'none',
                    padding: 0
                  }}
                />
              </Popconfirm>
            </Tooltip>
          )}
          {!isGuest && (
            <Tooltip title="Xóa">
              <Popconfirm
                title="Xóa hồ sơ sơ bộ"
                description="Bạn có chắc chắn muốn xóa hồ sơ này?"
                onConfirm={() => onDelete(record.id)}
                okText="Xóa"
                cancelText="Hủy"
                okButtonProps={{ danger: true }}
              >
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined style={{ fontSize: '18px' }} />}
                  style={{ 
                    width: '36px', 
                    height: '36px', 
                    minWidth: '36px', 
                    display: 'flex', 
                    justifyContent: 'center', 
                    alignItems: 'center', 
                    borderRadius: '6px', 
                    backgroundColor: '#fef2f2', 
                    border: 'none', 
                    padding: 0 
                  }}
                />
              </Popconfirm>
            </Tooltip>
          )}
          {isGuest && (
            <Tooltip title="Xem chi tiết">
              <Button
                type="text"
                icon={<EyeOutlined style={{ color: '#007f7a', fontSize: '18px' }} />}
                onClick={() => onView(record)}
                style={{ 
                  width: '36px', 
                  height: '36px', 
                  minWidth: '36px', 
                  display: 'flex', 
                  justifyContent: 'center', 
                  alignItems: 'center', 
                  borderRadius: '6px', 
                  backgroundColor: '#f1f5f9', 
                  border: 'none', 
                  padding: 0 
                }}
              />
            </Tooltip>
          )}
        </div>
      )
    }
  ];

  const previewContent = previewRecord?.response_content || '';
  const previewIsHtml = isHtmlContent(previewContent);

  return (
    <>
      <style>{`
        .sobo-compact-header {
          display: inline-block;
          max-width: 100%;
          white-space: normal;
          line-height: 1.35;
          overflow-wrap: anywhere;
          text-align: center;
        }
        .sobo-id-date-cell {
          min-width: 0;
          overflow-wrap: anywhere;
        }
        .sobo-status-pill {
          max-width: 100%;
          justify-content: center;
          white-space: normal;
          line-height: 1.25;
          text-align: center;
        }
        .sobo-response-preview,
        .sobo-response-preview * {
          max-width: 100%;
          box-sizing: border-box;
          overflow-wrap: anywhere;
          word-break: break-word;
        }
        .sobo-response-preview table {
          width: 100% !important;
          table-layout: fixed;
        }
        .sobo-response-preview img {
          height: auto;
          max-width: 100% !important;
        }
      `}</style>
      <div style={{ background: '#ffffff', borderRadius: '12px', border: '1px solid #e5ebf0', overflow: 'hidden' }}>
        <Table
          bordered
          {...getResizableProps(columns)}
          dataSource={dataSource}
          rowKey="id"
          loading={loading}
          tableLayout="fixed"
          scroll={{ x: 1230 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            pageSizeOptions: pagination.pageSizeOptions || ['10', '20', '50'],
            showTotal: (total) => `Tổng số: ${total} hồ sơ`
          }}
          onChange={(pag) => onChange({ current: pag.current, pageSize: pag.pageSize })}
          onRow={(record) => ({
            onClick: () => onView(record),
            style: { cursor: 'pointer' }
          })}
        />
      </div>

      {/* Modal xem nội dung mail phản hồi */}
      <Modal
        open={!!previewRecord}
        onCancel={() => setPreviewRecord(null)}
        footer={null}
        width={1100}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MailOutlined style={{ color: '#2563eb' }} />
            <span style={{ fontWeight: 700, fontSize: '15px', color: '#0f172a' }}>
              Mail phản hồi – Hồ sơ #{previewRecord?.id}
            </span>
          </div>
        }
        styles={{
          body: { padding: '16px 20px', maxHeight: '70vh', overflowY: 'auto' }
        }}
      >
        {previewRecord && (
          <>
            {/* Thông tin người gửi / tiêu đề */}
            <div style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '10px 14px',
              marginBottom: '16px',
              fontSize: '12px',
              color: '#64748b'
            }}>
              <div><strong style={{ color: '#334155' }}>Chủ đề:</strong> {previewRecord.outbound_subject || '-'}</div>
              <div style={{ marginTop: '4px' }}><strong style={{ color: '#334155' }}>Người phản hồi:</strong> {previewRecord.email_recipient || '-'}</div>
            </div>

            {/* Nội dung email */}
            {previewIsHtml ? (
              <div
                style={{
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '16px',
                  background: '#fff',
                  lineHeight: 1.6,
                }}
              >
                <style>{EMAIL_HTML_STYLES}</style>
                <div dangerouslySetInnerHTML={{ __html: previewContent }} />
              </div>
            ) : (
              <div style={{
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '16px',
                background: '#fff',
                fontSize: '13px',
                color: '#374151',
                whiteSpace: 'pre-wrap',
                lineHeight: 1.7,
              }}>
                {previewContent}
              </div>
            )}
          </>
        )}
      </Modal>
    </>
  );
}
