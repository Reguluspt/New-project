import React, { useState } from 'react';
import { Upload, message, Progress, Card, Button } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { uploadFiles } from '../../api/entry';

const { Dragger } = Upload;

export default function FileUploader({ onUploadSuccess }) {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [fileList, setFileList] = useState([]);

  const handleUpload = async () => {
    if (!fileList.length) {
      message.warning('Vui lòng chọn ít nhất một file GCN.');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    const formData = new FormData();
    fileList.forEach((file) => formData.append('files', file.originFileObj || file));

    try {
      const res = await uploadFiles(formData, (percent) => {
        setUploadProgress(percent);
      });
      
      message.success(`Đã tải lên ${fileList.length} file.`);
      setFileList([]);
      
      if (onUploadSuccess && res.data) {
        onUploadSuccess(res.data.upload_id, res.data.files);
      }
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Tải file thất bại.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card 
      style={{ borderRadius: 10, border: '1px dashed #d8e7e5', padding: 4 }}
      bodyStyle={{ padding: 12 }}
    >
      <Dragger
        name="files"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.webp"
        beforeUpload={(file) => {
          setFileList((current) => [...current, file]);
          return false;
        }}
        onRemove={(file) => {
          setFileList((current) => current.filter((item) => item.uid !== file.uid));
        }}
        fileList={fileList}
        showUploadList
        disabled={uploading}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined style={{ color: '#007f7a' }} />
        </p>
        <p className="ant-upload-text" style={{ fontSize: 15, fontWeight: 500 }}>
          Kéo thả hoặc Click để tải lên GCN
        </p>
        <p className="ant-upload-hint" style={{ fontSize: 12, color: '#8c8c8c' }}>
          Hỗ trợ file PDF hoặc ảnh quét (PNG, JPG, JPEG, WebP)
        </p>
      </Dragger>

      <Button
        type="primary"
        onClick={handleUpload}
        loading={uploading}
        disabled={!fileList.length}
        style={{ marginTop: 12, width: '100%' }}
      >
        Tải {fileList.length || ''} file để quét
      </Button>

      {uploading && (
        <div style={{ marginTop: 12, textAlign: 'center' }}>
          <span style={{ fontSize: 13, color: '#595959' }}>Đang tải lên và xử lý các trang...</span>
          <Progress percent={uploadProgress} size="small" status="active" style={{ marginTop: 4 }} />
        </div>
      )}
    </Card>
  );
}
