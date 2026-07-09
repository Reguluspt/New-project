import React from 'react';
import { Drawer, Button, Space, message, Spin } from 'antd';
import { DownloadOutlined, PrinterOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons';
import { downloadDocument } from '../../api/documents';

export default function DocumentPreview({ open, onClose, caseId, filename }) {
  const handleDownload = async () => {
    try {
      const response = await downloadDocument(caseId, filename);
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error(err);
      message.error('Tải file thất bại');
    }
  };

  const handlePrint = () => {
    const iframe = document.getElementById('preview-iframe');
    if (iframe) {
      try {
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
      } catch (err) {
        console.error(err);
        message.error('Không thể kích hoạt in. Trình duyệt có thể đang chặn quyền truy cập iframe.');
      }
    }
  };

  const previewUrl = `/api/cases/${caseId}/documents/${filename}/preview`;

  return (
    <Drawer
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', paddingRight: 24 }}>
          <Space>
            <EyeOutlined style={{ color: '#007f7a' }} />
            <span style={{ fontWeight: 600 }}>Xem trước: {filename}</span>
          </Space>
          <Space>
            <Button 
              icon={<DownloadOutlined />} 
              onClick={handleDownload}
              style={{ borderRadius: 6 }}
            >
              Tải về
            </Button>
            <Button 
              type="primary"
              icon={<PrinterOutlined />} 
              onClick={handlePrint}
              style={{ borderRadius: 6 }}
            >
              In văn bản
            </Button>
          </Space>
        </div>
      }
      placement="right"
      width={850}
      onClose={onClose}
      open={open}
      extra={
        <Button 
          type="text" 
          icon={<CloseOutlined />} 
          onClick={onClose} 
        />
      }
      closable={false}
      bodyStyle={{ padding: 0, background: '#f3f4f6' }}
      destroyOnClose
    >
      <div style={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', position: 'relative' }}>
        <iframe
          id="preview-iframe"
          src={previewUrl}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            background: '#ffffff',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
          }}
          title="Document Preview"
        />
      </div>
    </Drawer>
  );
}
