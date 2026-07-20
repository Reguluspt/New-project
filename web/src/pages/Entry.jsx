import { useState } from 'react';
import { Row, Col, Card, Typography, Space, Button, message, Select, Tag } from 'antd';
import { FilePdfOutlined, UploadOutlined } from '@ant-design/icons';
import FileUploader from '../components/entry/FileUploader';
import PageViewer from '../components/entry/PageViewer';
import OcrActions from '../components/entry/OcrActions';
import EntryForm from '../components/entry/EntryForm';

const { Title, Text } = Typography;

const extractedValue = (asset, field) => {
  const value = asset?.[field];
  return typeof value === 'object' ? value?.value || '' : value || '';
};

const assetDescriptionFromExtraction = (asset) => {
  const assetDescription = String(asset?.asset_description || '').trim();
  if (assetDescription) return assetDescription;

  const landParcel = extractedValue(asset, 'so_thua_dat') || extractedValue(asset, 'so_thua');
  const mapSheet = extractedValue(asset, 'so_to_ban_do') || extractedValue(asset, 'so_to');
  const address = extractedValue(asset, 'dia_chi_thua_dat') || extractedValue(asset, 'land_address');
  if (!landParcel && !mapSheet && !address) return '';
  return `Thửa đất số ${landParcel}, tờ bản đồ số ${mapSheet}; tại địa chỉ ${address}`;
};

export default function Entry() {
  const [uploadId, setUploadId] = useState(null);
  const [files, setFiles] = useState([]);
  const [activeFileIndex, setActiveFileIndex] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [ocrData, setOcrData] = useState(null);
  const [, setScannedResults] = useState({});

  const handleUploadSuccess = (newUploadId, uploadedFiles) => {
    setUploadId(newUploadId);
    setFiles((uploadedFiles || []).map((file) => ({
      ...file,
      scanStatus: 'pending',
      extraction: null,
      multiExtraction: null,
      scanError: '',
    })));
    setActiveFileIndex(0);
    setCurrentPage(1);
    setRotation(0);
    setOcrData(null);
    setScannedResults({});
  };

  const handleReset = () => {
    setUploadId(null);
    setFiles([]);
    setActiveFileIndex(0);
    setCurrentPage(1);
    setRotation(0);
    setOcrData(null);
    setScannedResults({});
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

  const handleFileScanned = (fileId, extraction, multiExtraction) => {
    setScannedResults((currentResults) => {
      const scannedFile = files.find((file) => file.file_id === fileId);
      const nextResults = {
        ...currentResults,
        [fileId]: {
          extraction,
          multiExtraction,
          sourceFileName: scannedFile?.name || '',
        },
      };
      const extractedFiles = Object.values(nextResults);
      const primaryExtraction = extractedFiles[0]?.extraction || extraction;
      const assetDescriptions = [...new Set(extractedFiles.flatMap(({ extraction: fileExtraction, multiExtraction: fileMultiExtraction }) => {
        const assets = Array.isArray(fileMultiExtraction?.assets) && fileMultiExtraction.assets.length
          ? fileMultiExtraction.assets
          : [fileExtraction];
        return assets.map(assetDescriptionFromExtraction).filter(Boolean);
      }))];
      const gcnDetails = extractedFiles.flatMap(({ extraction: fileExtraction, multiExtraction: fileMultiExtraction, sourceFileName }, fileIndex) => {
        const assets = Array.isArray(fileMultiExtraction?.assets) && fileMultiExtraction.assets.length
          ? fileMultiExtraction.assets
          : [fileExtraction];
        return assets.map((asset, assetIndex) => ({
          ...asset,
          source_file_id: Object.keys(nextResults)[fileIndex],
          source_file_name: sourceFileName,
          asset_index: assetIndex,
        }));
      });

      setOcrData({
        ...primaryExtraction,
        asset_description: assetDescriptions.join('\n'),
        gcn_details: gcnDetails,
      });
      return nextResults;
    });
  };

  const handleFileScanState = (fileId, changes) => {
    setFiles((currentFiles) => currentFiles.map((file) => (
      file.file_id === fileId ? { ...file, ...changes } : file
    )));
  };

  const scanStatusLabel = (status) => ({
    pending: 'Chờ quét',
    processing: 'Đang quét',
    applied: 'Đã đưa vào form',
    error: 'Lỗi quét',
  }[status] || 'Chờ quét');

  const scanStatusColor = (status) => ({
    pending: 'default',
    processing: 'processing',
    applied: 'success',
    error: 'error',
  }[status] || 'default');

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
                  label: `${index + 1}. ${file.name} (${scanStatusLabel(file.scanStatus)})`,
                }))}
              />
            )}
            {activeFile && (
              <Tag color={scanStatusColor(activeFile.scanStatus)}>
                {scanStatusLabel(activeFile.scanStatus)}
              </Tag>
            )}
            <OcrActions 
              uploadId={uploadId} 
              activeFile={activeFile} 
              files={files}
              onFileScanState={handleFileScanState}
              onFileScanned={handleFileScanned}
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
