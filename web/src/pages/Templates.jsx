import React, { useState, useEffect, useCallback } from 'react';
import { Card, Typography, Table, Button, Space, message } from 'antd';
import { FileWordOutlined, EyeOutlined } from '@ant-design/icons';
import { getTemplates } from '../api/templates';
import TemplateEditor from '../components/templates/TemplateEditor';

const { Title, Paragraph } = Typography;

export default function Templates() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedTemplateName, setSelectedTemplateName] = useState(null);
  const [editorOpen, setEditorOpen] = useState(false);

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getTemplates();
      setTemplates(res.data || []);
    } catch (err) {
      console.error(err);
      message.error('Lỗi khi tải danh sách mẫu thiết kế (.docx)');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleRowClick = (record) => {
    setSelectedTemplateName(record.name);
    setEditorOpen(true);
  };

  const handleEditorClose = () => {
    setEditorOpen(false);
    setSelectedTemplateName(null);
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

  const columns = [
    {
      title: 'Tên mẫu Word',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (text) => (
        <Space>
          <FileWordOutlined style={{ fontSize: '18px', color: '#0f6cbd' }} />
          <strong>{text}</strong>
        </Space>
      )
    },
    {
      title: 'Thư mục chứa mẫu',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      render: (path) => <span style={{ fontSize: '12px', color: '#64748b' }}>{path}</span>
    },
    {
      title: 'Dung lượng',
      dataIndex: 'size',
      key: 'size',
      width: 130,
      sorter: (a, b) => a.size - b.size,
      render: (size) => `${(size / 1024).toFixed(1)} KB`
    },
    {
      title: 'Cập nhật lần cuối',
      dataIndex: 'last_modified',
      key: 'last_modified',
      width: 180,
      render: (val) => formatDate(val)
    },
    {
      title: 'Thao tác',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Button
          type="primary"
          ghost
          size="small"
          icon={<EyeOutlined />}
          onClick={(e) => {
            e.stopPropagation(); // prevent row click
            handleRowClick(record);
          }}
        >
          Chi tiết
        </Button>
      )
    }
  ];

  return (
    <div>
      {/* Title Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0, fontWeight: 700 }}>
          📄 Quản lý Mẫu văn bản (Templates)
        </Title>
        <Paragraph style={{ color: '#64748b', margin: '4px 0 0 0' }}>
          Quản lý các tệp mẫu Word (.docx) dùng để xuất bản hợp đồng, biên bản nghiệm thu, phiếu yêu cầu sơ bộ. Tải lên và theo dõi lịch sử phiên bản của từng mẫu.
        </Paragraph>
      </div>

      <Card>
        <Table
          dataSource={templates}
          columns={columns}
          rowKey="name"
          loading={loading}
          pagination={{ pageSize: 10 }}
          onRow={(record) => ({
            onClick: () => handleRowClick(record),
            style: { cursor: 'pointer' }
          })}
          size="middle"
          style={{ background: '#ffffff', borderRadius: '8px', overflow: 'hidden' }}
        />
      </Card>

      {/* Detail & Editor Drawer */}
      <TemplateEditor
        open={editorOpen}
        templateName={selectedTemplateName}
        onClose={handleEditorClose}
        onSuccess={fetchTemplates}
      />
    </div>
  );
}
