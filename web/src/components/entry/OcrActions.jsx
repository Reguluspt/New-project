import { useMemo, useState } from 'react';
import { Alert, Button, Divider, Modal, Progress, Select, Space, Spin, Tag, message } from 'antd';
import { ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { extractFields } from '../../api/entry';

const STATUS = {
  pending: { label: 'Chờ quét', color: 'default' },
  processing: { label: 'Đang quét', color: 'processing' },
  applied: { label: 'Đã đưa vào form', color: 'success' },
  error: { label: 'Lỗi quét', color: 'error' },
  skipped: { label: 'Đã ghép vào PDF', color: 'default' },
};

const allPagesFor = (file) => Array.from({ length: file.pages || 0 }, (_, index) => index + 1);

export default function OcrActions({ uploadId, activeFile, files = [], onFileScanState, onFileScanned }) {
  const [open, setOpen] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [provider, setProvider] = useState('Gemini');
  const [model, setModel] = useState('gemini-2.5-flash');

  const pendingFiles = useMemo(
    () => files.filter((file) => file.scanStatus === 'pending' || file.scanStatus === 'error'),
    [files],
  );

  const handleOpen = () => {
    if (!uploadId || !activeFile?.file_id) {
      message.warning('Vui lòng tải lên và chọn file GCN trước khi quét.');
      return;
    }
    setOpen(true);
  };

  const scanFilesSequentially = async (targets) => {
    if (!targets.length) {
      message.info('Không còn file nào cần quét.');
      return;
    }

    setExtracting(true);
    let completedCount = 0;
    try {
      for (const file of targets) {
        onFileScanState(file.file_id, { scanStatus: 'processing', scanError: '' });
        try {
          const response = await extractFields({
            upload_id: uploadId,
            file_id: file.file_id,
            pages: allPagesFor(file),
            provider,
            model,
            extract_all: false,
          });
          const extraction = response.data?.extraction || {};
          const multiExtraction = response.data?.multi_extraction || {};
          const assetCount = Array.isArray(multiExtraction.assets) ? multiExtraction.assets.length : 0;
          onFileScanState(file.file_id, {
            scanStatus: 'applied',
            extraction,
            multiExtraction,
            assetCount,
            scanError: '',
          });
          onFileScanned?.(file.file_id, extraction, multiExtraction);
          completedCount += 1;
        } catch (error) {
          console.error(error);
          onFileScanState(file.file_id, {
            scanStatus: 'error',
            scanError: error.response?.data?.error || 'Không thể trích xuất file này.',
          });
        }
      }
    } finally {
      setExtracting(false);
    }

    if (completedCount) {
      message.success(`Đã quét và đưa ${completedCount}/${targets.length} file vào form.`);
    }
  };

  return (
    <>
      <Button
        type="primary"
        icon={<ThunderboltOutlined />}
        onClick={handleOpen}
        disabled={!uploadId}
        style={{ background: '#007f7a', borderColor: '#007f7a', borderRadius: 6 }}
      >
        Quét GCN
      </Button>

      <Modal
        open={open}
        title="Hàng đợi quét GCN"
        onCancel={() => !extracting && setOpen(false)}
        closable={!extracting}
        footer={[
          <Button key="close" onClick={() => setOpen(false)} disabled={extracting}>Đóng</Button>,
          <Button
            key="scan-pending"
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={extracting}
            disabled={!pendingFiles.length}
            onClick={() => scanFilesSequentially(pendingFiles)}
            style={{ background: '#007f7a', borderColor: '#007f7a' }}
          >
            Quét {pendingFiles.length} file chờ
          </Button>,
        ]}
        width={720}
        destroyOnClose={false}
      >
        <Alert
          type="info"
          showIcon
          message="Các file được quét theo thứ tự. Sau khi quét xong, tài sản được tự động đưa vào form."
          style={{ marginBottom: 16 }}
        />

        <Spin spinning={extracting} tip="AI đang quét file trong hàng đợi...">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {files.map((file) => {
              const status = STATUS[file.scanStatus] || STATUS.pending;
              const isActive = file.file_id === activeFile?.file_id;
              return (
                <div
                  key={file.file_id}
                  style={{
                    border: `1px solid ${isActive ? '#8fcfc9' : '#d8e7e5'}`,
                    borderRadius: 6,
                    padding: '11px 12px',
                    background: isActive ? '#f0faf8' : '#fff',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {file.name}
                      </div>
                      <div style={{ color: '#64748b', fontSize: 12, marginTop: 3 }}>
                        {file.pages} trang{file.assetCount ? ` · AI nhận diện ${file.assetCount} tài sản` : ''}
                      </div>
                    </div>
                    <Tag color={status.color}>{status.label}</Tag>
                  </div>
                  {file.scanStatus === 'processing' && <Progress percent={50} size="small" status="active" style={{ marginTop: 9 }} />}
                  {file.scanError && <div style={{ color: '#b42318', fontSize: 12, marginTop: 7 }}>{file.scanError}</div>}
                </div>
              );
            })}
          </div>
        </Spin>

        <Divider style={{ margin: '18px 0 14px' }} />
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, marginBottom: 6 }}>Nhà cung cấp</div>
              <Select
                value={provider}
                onChange={(value) => {
                  setProvider(value);
                  setModel(value === 'Gemini' ? 'gemini-2.5-flash' : 'gpt-4o-mini');
                }}
                disabled={extracting}
                style={{ width: '100%' }}
                options={[{ value: 'Gemini', label: 'Google Gemini' }, { value: 'OpenAI', label: 'OpenAI GPT' }]}
              />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, marginBottom: 6 }}>Model AI</div>
              <Select
                value={model}
                onChange={setModel}
                disabled={extracting}
                style={{ width: '100%' }}
                options={provider === 'Gemini'
                  ? [{ value: 'gemini-2.5-flash', label: 'gemini-2.5-flash' }, { value: 'gemini-2.5-pro', label: 'gemini-2.5-pro' }]
                  : [{ value: 'gpt-4o-mini', label: 'gpt-4o-mini' }, { value: 'gpt-4o', label: 'gpt-4o' }]}
              />
            </div>
          </div>

          <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
            <div>
              <div style={{ fontWeight: 600 }}>File đang xem: {activeFile?.name || 'Chưa chọn'}</div>
              <div style={{ color: '#64748b', fontSize: 12, marginTop: 3 }}>Quét lại sẽ thay thế phần tài sản của file này trong form.</div>
            </div>
            <Button
              icon={<ReloadOutlined />}
              disabled={extracting || !activeFile || activeFile.scanStatus === 'skipped'}
              onClick={() => scanFilesSequentially([activeFile])}
            >
              Quét lại file này
            </Button>
          </div>
        </Space>
      </Modal>
    </>
  );
}
