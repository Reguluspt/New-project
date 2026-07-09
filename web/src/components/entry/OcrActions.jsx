import React, { useState } from 'react';
import { Card, Button, Checkbox, Modal, Space, Select, Descriptions, message, Spin, Alert } from 'antd';
import { EyeOutlined, CheckCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { extractFields } from '../../api/entry';

export default function OcrActions({ uploadId, activeFile, files = [], onApplyData }) {
  const [open, setOpen] = useState(false);
  const [selectedPages, setSelectedPages] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [extractedResult, setExtractedResult] = useState(null);
  const [provider, setProvider] = useState('Gemini');
  const [model, setModel] = useState('gemini-2.5-flash');
  const [scanAll, setScanAll] = useState(true);

  const pageCount = activeFile?.pages || 0;

  const handleOpen = () => {
    if (!uploadId) {
      message.warning('Vui lòng upload tài liệu trước khi trích xuất');
      return;
    }
    if (!activeFile?.file_id) {
      message.warning('Vui lòng chọn file cần trích xuất');
      return;
    }
    // Default select all pages
    const allPages = Array.from({ length: pageCount }, (_, i) => i + 1);
    setSelectedPages(allPages);
    setScanAll(true);
    setOpen(true);
  };

  const handleExtract = async () => {
    if (!scanAll && selectedPages.length === 0) {
      message.warning('Vui lòng chọn ít nhất một trang để trích xuất');
      return;
    }

    setExtracting(true);
    try {
      const res = await extractFields({
        upload_id: uploadId,
        file_id: activeFile.file_id,
        pages: selectedPages,
        provider: provider,
        model: model,
        extract_all: scanAll
      });

      setExtractedResult(res.data?.extraction || {});
      message.success('Trích xuất thông tin AI hoàn tất! 🔮');
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Trích xuất thất bại. Vui lòng kiểm tra lại API Key.');
    } finally {
      setExtracting(false);
    }
  };

  const handleApply = () => {
    if (onApplyData && extractedResult) {
      onApplyData(extractedResult);
      message.success('Đã áp dụng kết quả trích xuất vào form!');
      setOpen(false);
      setExtractedResult(null);
    }
  };

  return (
    <>
      <Button
        type="primary"
        icon={<ThunderboltOutlined />}
        onClick={handleOpen}
        disabled={!uploadId}
        style={{
          background: '#059669',
          borderColor: '#059669',
          borderRadius: 6
        }}
      >
        Trích xuất AI
      </Button>

      <Modal
        open={open}
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#059669' }} />
            <span>Trích xuất thông tin GCN bằng AI</span>
          </Space>
        }
        onCancel={() => setOpen(false)}
        footer={
          extractedResult ? [
            <Button key="back" onClick={() => setExtractedResult(null)}>Trích xuất lại</Button>,
            <Button 
              key="submit" 
              type="primary" 
              icon={<CheckCircleOutlined />} 
              onClick={handleApply}
              style={{ background: '#059669', borderColor: '#059669' }}
            >
              Áp dụng kết quả
            </Button>
          ] : [
            <Button key="cancel" onClick={() => setOpen(false)}>Hủy</Button>,
            <Button 
              key="extract" 
              type="primary" 
              loading={extracting} 
              onClick={handleExtract}
              style={{ background: '#059669', borderColor: '#059669' }}
            >
              Bắt đầu trích xuất
            </Button>
          ]
        }
        width={650}
        destroyOnClose
        style={{ borderRadius: 10 }}
      >
        {!extractedResult ? (
          <Spin spinning={extracting} tip={scanAll ? "AI đang đọc và trích xuất dữ liệu từ tất cả các file đã tải lên (khoảng 10-35s)..." : "AI đang đọc và trích xuất dữ liệu từ các trang đã chọn (khoảng 10-25s)..."}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 12 }}>
              <Alert 
                message="Chọn trang và mô hình AI phù hợp. Lưu ý chọn các trang có sơ đồ thửa đất, thông tin chủ sở hữu và trang thay đổi/bien động." 
                type="info" 
                showIcon 
              />
              
              <div>
                <Checkbox 
                  checked={scanAll} 
                  onChange={(e) => setScanAll(e.target.checked)}
                  style={{ fontWeight: 500, marginBottom: 8 }}
                >
                  Quét tất cả các file đã tải lên (Mặc định)
                </Checkbox>
              </div>

              {!scanAll && (
                <div>
                  <span style={{ fontWeight: 500, display: 'block', marginBottom: 8 }}>Chọn trang GCN trích xuất:</span>
                  <Checkbox.Group 
                    options={Array.from({ length: pageCount }, (_, i) => ({ label: `Trang ${i + 1}`, value: i + 1 }))}
                    value={selectedPages}
                    onChange={setSelectedPages}
                  />
                </div>
              )}

              <div style={{ display: 'flex', gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <span style={{ fontWeight: 500, display: 'block', marginBottom: 8 }}>Nhà cung cấp:</span>
                  <Select
                    value={provider}
                    onChange={(val) => {
                      setProvider(val);
                      setModel(val === 'Gemini' ? 'gemini-2.5-flash' : 'gpt-4o-mini');
                    }}
                    style={{ width: '100%' }}
                    options={[
                      { value: 'Gemini', label: 'Google Gemini' },
                      { value: 'OpenAI', label: 'OpenAI GPT' }
                    ]}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <span style={{ fontWeight: 500, display: 'block', marginBottom: 8 }}>Mô hình AI:</span>
                  <Select
                    value={model}
                    onChange={setModel}
                    style={{ width: '100%' }}
                    options={
                      provider === 'Gemini' 
                        ? [
                            { value: 'gemini-2.5-flash', label: 'gemini-2.5-flash (Nhanh, Tối ưu)' },
                            { value: 'gemini-2.5-pro', label: 'gemini-2.5-pro (Thông minh nhất)' }
                          ]
                        : [
                            { value: 'gpt-4o-mini', label: 'gpt-4o-mini (Nhanh)' },
                            { value: 'gpt-4o', label: 'gpt-4o (Đầy đủ)' }
                          ]
                    }
                  />
                </div>
              </div>
            </div>
          </Spin>
        ) : (
          <div style={{ marginTop: 12 }}>
            <Alert 
              message="Vui lòng đối chiếu kết quả trích xuất bên dưới trước khi áp dụng vào form nhập liệu." 
              type="success" 
              showIcon 
              style={{ marginBottom: 16 }}
            />
            
            <Descriptions title="Kết quả trích xuất từ AI" bordered column={1} size="small">
              <Descriptions.Item label="Số thửa đất">
                {extractedResult.so_thua_dat?.value || 'Không có'}
              </Descriptions.Item>
              <Descriptions.Item label="Số tờ bản đồ">
                {extractedResult.so_to_ban_do?.value || 'Không có'}
              </Descriptions.Item>
              <Descriptions.Item label="Địa chỉ thửa đất">
                {extractedResult.dia_chi_thua_dat?.value || 'Không có'}
              </Descriptions.Item>
              <Descriptions.Item label="Chủ sở hữu cuối cùng">
                {extractedResult.ten_chu_so_huu_cuoi_cung?.value || 'Không có'}
              </Descriptions.Item>
              <Descriptions.Item label="Địa chỉ chủ sở hữu">
                {extractedResult.dia_chi_chu_so_huu_cuoi_cung?.value || 'Không có'}
              </Descriptions.Item>
              <Descriptions.Item label="CCCD chủ sở hữu">
                {extractedResult.so_cccd_chu_so_huu_cuoi_cung?.value || 'Không có'}
              </Descriptions.Item>
              <Descriptions.Item label="Số giấy chứng nhận">
                {extractedResult.so_giay_chung_nhan?.value || 'Không có'}
              </Descriptions.Item>
              <Descriptions.Item label="Số vào sổ cấp giấy chứng nhận">
                {extractedResult.so_vao_so_cap_giay_chung_nhan?.value || 'Không có'}
              </Descriptions.Item>
              <Descriptions.Item label="Ngày cấp giấy chứng nhận">
                {extractedResult.ngay_cap_giay_chung_nhan?.value || 'Không có'}
              </Descriptions.Item>
              {extractedResult.notes && extractedResult.notes.length > 0 && (
                <Descriptions.Item label="Ghi chú AI">
                  <ul style={{ paddingLeft: 16, margin: 0 }}>
                    {extractedResult.notes.map((note, i) => <li key={i}>{note}</li>)}
                  </ul>
                </Descriptions.Item>
              )}
            </Descriptions>
          </div>
        )}
      </Modal>
    </>
  );
}
