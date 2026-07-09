import React, { useState } from 'react';
import { Row, Col, Card, Typography, Space, Button, message, Select } from 'antd';
import { FilePdfOutlined, UploadOutlined, HomeOutlined } from '@ant-design/icons';
import FileUploader from '../components/entry/FileUploader';
import PageViewer from '../components/entry/PageViewer';
import OcrActions from '../components/entry/OcrActions';
import EntryForm from '../components/entry/EntryForm';

const { Title, Text } = Typography;

export default function Entry() {
  const [uploadId, setUploadId] = useState(null);
  const [files, setFiles] = useState([]);
  const [activeFileIndex, setActiveFileIndex] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [ocrData, setOcrData] = useState(null);

  const handleUploadSuccess = (newUploadId, uploadedFiles) => {
    setUploadId(newUploadId);
    setFiles(uploadedFiles || []);
    setActiveFileIndex(0);
    setCurrentPage(1);
    setRotation(0);
    setOcrData(null);
  };

  const handleReset = () => {
    setUploadId(null);
    setFiles([]);
    setActiveFileIndex(0);
    setCurrentPage(1);
    setRotation(0);
    setOcrData(null);
  };

  const handlePageChange = (pageNum) => {
    setCurrentPage(pageNum);
    // Reset rotation when changing pages, or keep it. Streamlit resets or keeps.
    // Let's keep it to let user rotate page and keep viewing.
  };

  const handleFileChange = (fileIndex) => {
    setActiveFileIndex(fileIndex);
    setCurrentPage(1);
    setRotation(0);
    setOcrData(null);
  };

  const handleApplyOcrData = (data) => {
    setOcrData(data);
  };

  const handleSaveSuccess = (caseId) => {
    // Redirect or reset page
    message.success(`Hồ sơ đã được lưu trữ với ID: ${caseId}`);
    handleReset();
  };

  const activeFile = files[activeFileIndex];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header and Workspace Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Nhập hồ sơ thẩm định mới</Title>
          <Text type="secondary">Tải lên tài liệu GCN, trích xuất dữ liệu tự động bằng AI và lưu thông tin vào cơ sở dữ liệu.</Text>
        </div>

        {uploadId && (
          <Space>
            {files.length > 1 && (
              <Select
                value={activeFileIndex}
                onChange={handleFileChange}
                style={{ minWidth: 240 }}
                options={files.map((file, index) => ({
                  value: index,
                  label: `${index + 1}. ${file.name}`,
                }))}
              />
            )}
            <OcrActions 
              uploadId={uploadId} 
              activeFile={activeFile} 
              files={files}
              onApplyData={handleApplyOcrData} 
            />
            <Button 
              icon={<UploadOutlined />} 
              onClick={handleReset}
              style={{ borderRadius: 6 }}
            >
              Chọn tài liệu khác
            </Button>
          </Space>
        )}
      </div>

      {/* Main Workspace Layout */}
      <Row gutter={[16, 16]}>
        {/* Left Panel: PDF/Image Document Viewer or File Uploader */}
        <Col xs={24} lg={12}>
          {!uploadId ? (
            <Card 
              style={{ borderRadius: 12, border: '1px solid #d8e7e5', minHeight: '400px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}
              styles={{ body: { padding: '24px' } }}
            >
              <div style={{ textAlign: 'center', marginBottom: 24 }}>
                <FilePdfOutlined style={{ fontSize: 44, color: '#007f7a' }} />
                <Title level={4} style={{ marginTop: 12, marginBottom: 8 }}>Bắt đầu bằng cách tải lên hồ sơ GCN</Title>
                <Text type="secondary" style={{ fontSize: '13px' }}>AI sẽ tự động nhận diện và trích xuất thông tin.</Text>
              </div>
              <FileUploader onUploadSuccess={handleUploadSuccess} />
            </Card>
          ) : (
            <PageViewer 
              uploadId={uploadId}
              activeFile={activeFile}
              currentPage={currentPage}
              onPageChange={handlePageChange}
              rotation={rotation}
              onRotationChange={setRotation}
            />
          )}
        </Col>

        {/* Right Panel: Entry Form */}
        <Col xs={24} lg={12}>
          <EntryForm 
            uploadId={uploadId}
            formValues={ocrData}
            onSaveSuccess={handleSaveSuccess}
          />
        </Col>
      </Row>
    </div>
  );
}
