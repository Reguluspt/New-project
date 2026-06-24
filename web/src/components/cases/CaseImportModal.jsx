import React, { useState } from 'react';
import { Modal, Upload, message, Progress, Space, Button, Alert } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { importCases } from '../../api/cases';

const { Dragger } = Upload;

export default function CaseImportModal({ open, onCancel, onSuccess }) {
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.error("Vui lòng chọn hoặc kéo thả file Excel vào vùng upload!");
      return;
    }

    const file = fileList[0];
    setUploading(true);
    setProgress(30);

    try {
      setProgress(60);
      const res = await importCases(file);
      setProgress(100);
      
      if (res.data && res.data.success) {
        message.success(`Import thành công! Đã tạo thêm ${res.data.imported} hồ sơ.`);
        setFileList([]);
        onSuccess();
      } else {
        throw new Error("Không thể hoàn thành import");
      }
    } catch (err) {
      message.error(err.response?.data?.error || "Import file thất bại. Kiểm tra định dạng file Excel.");
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  const uploadProps = {
    onRemove: () => {
      setFileList([]);
    },
    beforeUpload: (file) => {
      // Validate file extension
      const isExcel = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || file.name.endsWith('.xlsx');
      if (!isExcel) {
        message.error('Chỉ hỗ trợ upload file Excel định dạng .xlsx!');
        return Upload.LIST_IGNORE;
      }
      setFileList([file]);
      return false; // prevent auto upload
    },
    fileList,
    maxCount: 1
  };

  return (
    <Modal
      open={open}
      title="Nhập hồ sơ từ file Excel (.xlsx)"
      onCancel={onCancel}
      footer={[
        <Button key="back" onClick={onCancel} disabled={uploading}>
          Hủy
        </Button>,
        <Button
          key="submit"
          type="primary"
          onClick={handleUpload}
          loading={uploading}
          disabled={fileList.length === 0}
        >
          Bắt đầu Import
        </Button>
      ]}
      width={600}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%', marginTop: 10 }}>
        <Alert
          message="Hướng dẫn Import"
          description="File Excel của bạn cần chứa các cột bắt buộc: 'Khách hàng', 'Địa chỉ', 'Tài sản thẩm định', 'Mục đích thẩm định', 'Phí thẩm định'. File import sẽ tự động bỏ qua các dòng trùng lặp đã tồn tại trong cơ sở dữ liệu."
          type="info"
          showIcon
        />

        <Dragger {...uploadProps} disabled={uploading}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">Kéo thả file Excel vào đây hoặc click để chọn file</p>
          <p className="ant-upload-hint">
            Hỗ trợ file Excel .xlsx đơn lẻ.
          </p>
        </Dragger>

        {uploading && (
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 13, color: '#475569', marginBottom: 4 }}>Đang xử lý dữ liệu...</div>
            <Progress percent={progress} status="active" />
          </div>
        )}
      </Space>
    </Modal>
  );
}
