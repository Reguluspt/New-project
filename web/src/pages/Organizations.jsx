import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Typography,
  Table,
  Button,
  Input,
  Space,
  Modal,
  Form,
  Upload,
  message,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Divider,
  Select,
  Alert
} from 'antd';
import { useResizableColumns } from '../hooks/useResizableColumns';
import {
  SearchOutlined,
  PlusOutlined,
  MergeCellsOutlined,
  RobotOutlined,
  InboxOutlined,
  EditOutlined,
  DeleteOutlined,
  SaveOutlined,
  BankOutlined
} from '@ant-design/icons';
import {
  getOrganizations,
  createOrganization,
  updateOrganization,
  deleteOrganization,
  mergeOrganizations,
  extractOrganizationAi
} from '../api/organizations';

const { Title, Paragraph, Text } = Typography;

export default function Organizations() {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  // Add/Edit Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingOrg, setEditingOrg] = useState(null);
  const [form] = Form.useForm();

  // Merge Modal state
  const [mergeOpen, setMergeOpen] = useState(false);
  const [sourceId, setSourceId] = useState(null);
  const [targetId, setTargetId] = useState(null);
  const [merging, setMerging] = useState(false);

  // AI Extract state
  const [uploadList, setUploadList] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [extractedData, setExtractedData] = useState([]);

  // Fetch organizations
  const fetchOrgs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getOrganizations({ search: search.trim() });
      setOrgs(res.data || []);
    } catch (err) {
      console.error(err);
      message.error('Không thể tải danh sách tổ chức');
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    fetchOrgs();
  }, [fetchOrgs]);

  // Open modal for add
  const handleAddClick = () => {
    setEditingOrg(null);
    form.resetFields();
    setModalOpen(true);
  };

  // Open modal for edit
  const handleEditClick = (record) => {
    setEditingOrg(record);
    form.setFieldsValue({
      name: record.name,
      tax_code: record.tax_code,
      abbreviation: record.abbreviation,
      address: record.address,
      representative: record.representative,
      position: record.position,
    });
    setModalOpen(true);
  };

  // Handle Save (Add/Edit)
  const handleModalSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingOrg) {
        await updateOrganization(editingOrg.id, values);
        message.success('Cập nhật tổ chức thành công');
      } else {
        await createOrganization(values);
        message.success('Thêm tổ chức mới thành công');
      }
      setModalOpen(false);
      form.resetFields();
      fetchOrgs();
    } catch (err) {
      if (err.name !== 'ValidationError') {
        message.error('Lỗi lưu tổ chức: ' + (err.response?.data?.error || err.message));
      }
    }
  };

  // Handle Delete
  const handleDeleteClick = async (id) => {
    try {
      await deleteOrganization(id);
      message.success('Đã xóa tổ chức thành công');
      fetchOrgs();
    } catch (err) {
      message.error('Lỗi khi xóa tổ chức: ' + (err.response?.data?.error || err.message));
    }
  };

  // Handle Merge Organizations
  const handleMergeSubmit = async () => {
    if (!sourceId || !targetId) {
      message.warning('Vui lòng chọn đầy đủ tổ chức nguồn và đích');
      return;
    }
    if (sourceId === targetId) {
      message.warning('Tổ chức nguồn và đích không được trùng nhau');
      return;
    }

    setMerging(true);
    try {
      await mergeOrganizations(sourceId, targetId);
      message.success('Gộp tổ chức thành công!');
      setMergeOpen(false);
      setSourceId(null);
      setTargetId(null);
      fetchOrgs();
    } catch (err) {
      message.error('Lỗi gộp tổ chức: ' + (err.response?.data?.error || err.message));
    } finally {
      setMerging(false);
    }
  };

  // AI OCR Upload & Extraction
  const handleAiExtract = async () => {
    if (uploadList.length === 0) {
      message.warning('Vui lòng tải lên ít nhất một file hợp đồng');
      return;
    }

    setExtracting(true);
    const formData = new FormData();
    uploadList.forEach((file) => {
      formData.append('files', file);
    });

    const hide = message.loading('Đang chạy trích xuất thông tin bằng AI...', 0);
    try {
      const res = await extractOrganizationAi(formData);
      // Give each item a temp key for React Table list editing
      const resultsWithKeys = (res.data || []).map((item, idx) => ({
        ...item,
        key: `${Date.now()}_${idx}`
      }));
      setExtractedData(resultsWithKeys);
      setUploadList([]);
      message.success(`Trích xuất thành công ${resultsWithKeys.length} tổ chức!`);
    } catch (err) {
      message.error('Lỗi trích xuất AI: ' + (err.response?.data?.error || err.message));
    } finally {
      hide();
      setExtracting(false);
    }
  };

  // Inline edit handler for AI Extracted data
  const handleExtractedCellChange = (key, field, val) => {
    setExtractedData((prev) =>
      prev.map((item) => (item.key === key ? { ...item, [field]: val } : item))
    );
  };

  // Save AI results to Database
  const handleSaveExtractedToDb = async () => {
    let savedCount = 0;
    const hide = message.loading('Đang lưu các tổ chức vào danh bạ...', 0);
    try {
      for (const item of extractedData) {
        if (!item.name.trim()) continue;
        await createOrganization({
          name: item.name.trim(),
          tax_code: item.tax_code.trim(),
          abbreviation: item.abbreviation.trim(),
          address: item.address.trim(),
          representative: item.representative.trim(),
          position: item.position.trim(),
        });
        savedCount++;
      }
      message.success(`Đã lưu ${savedCount} tổ chức mới vào danh bạ!`);
      setExtractedData([]);
      fetchOrgs();
    } catch (err) {
      message.error('Lỗi lưu tổ chức trích xuất: ' + (err.response?.data?.error || err.message));
    } finally {
      hide();
    }
  };

  // Upload configuration
  const uploadProps = {
    onRemove: (file) => {
      setUploadList((prev) => prev.filter((f) => f.uid !== file.uid));
    },
    beforeUpload: (file) => {
      setUploadList((prev) => [...prev, file]);
      return false; // prevent automatic upload
    },
    fileList: uploadList,
    multiple: true,
  };

  const { getResizableProps } = useResizableColumns('organizations_list', {
    tax_code: 120,
    name: 300,
    abbreviation: 120,
    representative_info: 220,
    actions: 120
  });

  // Main columns
  const columns = [
    {
      title: 'MST',
      dataIndex: 'tax_code',
      key: 'tax_code',
      width: 120,
      render: (code) => <strong>{code || '-'}</strong>,
    },
    {
      title: 'Tên tổ chức',
      dataIndex: 'name',
      key: 'name',
      width: 300,
      render: (name) => <span style={{ fontWeight: 600, color: '#1e293b' }}>{name}</span>,
    },
    {
      title: 'Tên viết tắt',
      dataIndex: 'abbreviation',
      key: 'abbreviation',
      width: 120,
      render: (abbr) => abbr || '-',
    },
    {
      title: 'Người đại diện',
      key: 'representative_info',
      width: 220,
      render: (_, record) => {
        if (!record.representative) return '-';
        return `${record.representative} ${record.position ? `(${record.position})` : ''}`;
      },
    },
    {
      title: 'Thao tác',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EditOutlined style={{ color: '#eab308' }} />}
            onClick={() => handleEditClick(record)}
          />
          <Popconfirm
            title="Xóa tổ chức"
            description="Bạn chắc chắn muốn xóa tổ chức này khỏi danh bạ?"
            onConfirm={() => handleDeleteClick(record.id)}
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true }}
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // AI Extracted Table columns
  const extractedColumns = [
    {
      title: 'Mã số thuế',
      dataIndex: 'tax_code',
      key: 'tax_code',
      width: 130,
      render: (val, record) => (
        <Input
          value={val}
          onChange={(e) => handleExtractedCellChange(record.key, 'tax_code', e.target.value)}
          size="small"
        />
      ),
    },
    {
      title: 'Tên tổ chức *',
      dataIndex: 'name',
      key: 'name',
      render: (val, record) => (
        <Input
          value={val}
          onChange={(e) => handleExtractedCellChange(record.key, 'name', e.target.value)}
          size="small"
          status={!val ? 'error' : ''}
        />
      ),
    },
    {
      title: 'Địa chỉ',
      dataIndex: 'address',
      key: 'address',
      render: (val, record) => (
        <Input
          value={val}
          onChange={(e) => handleExtractedCellChange(record.key, 'address', e.target.value)}
          size="small"
        />
      ),
    },
    {
      title: 'Người đại diện',
      dataIndex: 'representative',
      key: 'representative',
      width: 140,
      render: (val, record) => (
        <Input
          value={val}
          onChange={(e) => handleExtractedCellChange(record.key, 'representative', e.target.value)}
          size="small"
        />
      ),
    },
    {
      title: 'Chức vụ',
      dataIndex: 'position',
      key: 'position',
      width: 110,
      render: (val, record) => (
        <Input
          value={val}
          onChange={(e) => handleExtractedCellChange(record.key, 'position', e.target.value)}
          size="small"
        />
      ),
    },
  ];

  // KPI calculations
  const totalOrgs = orgs.length;
  const hasTaxCode = orgs.filter((o) => o.tax_code && o.tax_code.trim()).length;
  const hasRep = orgs.filter((o) => o.representative && o.representative.trim()).length;

  return (
    <div>
      {/* Title Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0, fontWeight: 700 }}>
          📋 Danh bạ tổ chức
        </Title>
        <Paragraph style={{ color: '#64748b', margin: '4px 0 0 0' }}>
          Quản lý mã số thuế, địa chỉ, người đại diện và chức vụ để tự động điền khi nhập hồ sơ khách hàng doanh nghiệp.
        </Paragraph>
      </div>

      {/* KPI Stats Panel */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card bordered style={{ borderLeft: '5px solid #007f7a' }} hoverable>
            <Statistic title="Tổng tổ chức" value={totalOrgs} prefix={<BankOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card bordered style={{ borderLeft: '5px solid #047857' }} hoverable>
            <Statistic title="Đã có Mã Số Thuế" value={hasTaxCode} suffix={`/ ${totalOrgs}`} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card bordered style={{ borderLeft: '5px solid #eab308' }} hoverable>
            <Statistic title="Có Người Đại Diện" value={hasRep} suffix={`/ ${totalOrgs}`} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card bordered style={{ borderLeft: '5px solid #d99a55' }} hoverable>
            <Statistic title="Chờ duyệt từ AI" value={extractedData.length} />
          </Card>
        </Col>
      </Row>

      {/* Control Panel Grid */}
      <Row gutter={[24, 24]}>
        {/* Left Side: Table & AI Extraction */}
        <Col xs={24} lg={16}>
          <Card
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                <span>Danh sách tổ chức trong danh bạ</span>
                <Space>
                  <Button
                    type="primary"
                    ghost
                    icon={<MergeCellsOutlined />}
                    onClick={() => setMergeOpen(true)}
                  >
                    Gộp tổ chức
                  </Button>
                  <Button type="primary" icon={<PlusOutlined />} onClick={handleAddClick}>
                    Thêm tổ chức
                  </Button>
                </Space>
              </div>
            }
          >
            <Input
              placeholder="🔍 Tìm kiếm theo MST, Tên tổ chức, Người đại diện..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ marginBottom: 16 }}
              allowClear
              prefix={<SearchOutlined style={{ color: '#94a3b8' }} />}
            />
            <Table
              dataSource={orgs}
              {...getResizableProps(columns)}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 8 }}
              scroll={{ x: 'max-content' }}
              size="middle"
            />
          </Card>

          {/* AI Extraction Panel */}
          <Card
            title={
              <Space>
                <RobotOutlined style={{ color: '#d99a55' }} />
                <span>Trích xuất tổ chức từ hợp đồng bằng AI OCR</span>
              </Space>
            }
            style={{ marginTop: 24 }}
          >
            <Paragraph style={{ color: '#64748b' }}>
              Tải lên tài liệu hợp đồng cũ. AI sẽ tự động phân tích tên pháp nhân, mã số thuế, địa chỉ và thông tin người đại diện theo pháp luật.
            </Paragraph>
            
            <Upload.Dragger {...uploadProps} style={{ background: '#fafafa', padding: '16px 0' }}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined style={{ color: '#d99a55' }} />
              </p>
              <p className="ant-upload-text">Nhấp hoặc kéo thả file hợp đồng vào đây</p>
              <p className="ant-upload-hint">Hỗ trợ PDF, PNG, JPG, JPEG, DOCX. Cho phép tải lên nhiều file.</p>
            </Upload.Dragger>

            <Button
              type="primary"
              icon={<RobotOutlined />}
              onClick={handleAiExtract}
              loading={extracting}
              disabled={uploadList.length === 0}
              style={{ marginTop: 16, width: '100%', background: '#d99a55', borderColor: '#d99a55' }}
            >
              Trích xuất hàng loạt bằng AI Gemini
            </Button>

            {extractedData.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <Alert
                  type="info"
                  message="Dữ liệu trích xuất từ tài liệu. Vui lòng kiểm tra kỹ và chỉnh sửa trước khi lưu chính thức."
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Table
                  dataSource={extractedData}
                  columns={extractedColumns}
                  pagination={false}
                  size="small"
                  scroll={{ x: 600 }}
                />
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSaveExtractedToDb}
                  style={{ marginTop: 16, width: '100%' }}
                >
                  Lưu tất cả {extractedData.length} kết quả vào danh bạ
                </Button>
              </div>
            )}
          </Card>
        </Col>

        {/* Right Side: Quick Add/Edit Panel & Help */}
        <Col xs={24} lg={8}>
          <Card title="Hướng dẫn quản lý">
            <Paragraph>
              <ul>
                <li>
                  <strong>Tên viết tắt:</strong> Dùng để hiển thị ngắn gọn trên bảng hồ sơ và bộ lọc lọc nhanh.
                </li>
                <li>
                  <strong>Mã số thuế:</strong> Phải là duy nhất. Khi nhập hồ sơ khách hàng doanh nghiệp, hệ thống sẽ tự đối soát và đề xuất tự điền theo Mã số thuế này.
                </li>
                <li>
                  <strong>Gộp tổ chức:</strong> Sử dụng khi danh bạ bị trùng lặp tên/MST do nhập tay. Hồ sơ cũ liên kết với tổ chức nguồn sẽ được chuyển sang tổ chức đích.
                </li>
              </ul>
            </Paragraph>
          </Card>
        </Col>
      </Row>

      {/* Add / Edit Modal */}
      <Modal
        title={editingOrg ? `Cập nhật Tổ chức #${editingOrg.id}` : 'Thêm Tổ chức Mới'}
        open={modalOpen}
        onOk={handleModalSave}
        onCancel={() => setModalOpen(false)}
        okText="Lưu lại"
        cancelText="Hủy"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="Tên đầy đủ công ty / tổ chức"
            rules={[{ required: true, message: 'Tên tổ chức là bắt buộc' }]}
          >
            <Input placeholder="Ví dụ: Công ty Cổ phần Thẩm định giá Cenvalue" />
          </Form.Item>
          <Form.Item name="tax_code" label="Mã số thuế (MST)">
            <Input placeholder="Ví dụ: 0102712345" />
          </Form.Item>
          <Form.Item name="abbreviation" label="Tên viết tắt gợi nhớ">
            <Input placeholder="Ví dụ: Cenvalue" />
          </Form.Item>
          <Form.Item name="address" label="Địa chỉ trụ sở">
            <Input placeholder="Ví dụ: 137 Nguyễn Ngọc Vũ, Cầu Giấy, Hà Nội" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="representative" label="Người đại diện pháp luật">
                <Input placeholder="Nguyễn Văn A" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="position" label="Chức vụ người đại diện">
                <Input placeholder="Tổng giám đốc" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Merge Modal */}
      <Modal
        title={
          <Space>
            <MergeCellsOutlined style={{ color: '#007f7a' }} />
            <span>Gộp thông tin tổ chức</span>
          </Space>
        }
        open={mergeOpen}
        onOk={handleMergeSubmit}
        onCancel={() => {
          setMergeOpen(false);
          setSourceId(null);
          setTargetId(null);
        }}
        confirmLoading={merging}
        okText="Xác nhận gộp"
        cancelText="Hủy"
        destroyOnClose
      >
        <Paragraph>
          Hành động gộp sẽ chuyển tất cả các hồ sơ gắn với <strong>Tổ chức nguồn (Source)</strong> sang <strong>Tổ chức đích (Target)</strong>, sau đó xóa bản ghi Tổ chức nguồn.
        </Paragraph>
        <Form layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            label="Tổ chức nguồn (Sẽ bị XÓA sau khi gộp)"
            required
          >
            <Select
              placeholder="Chọn tổ chức nguồn..."
              value={sourceId}
              onChange={(val) => setSourceId(val)}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={orgs.map((o) => ({
                value: o.id,
                label: `${o.name} (MST: ${o.tax_code || 'chưa có'})`
              }))}
            />
          </Form.Item>
          
          <Form.Item
            label="Tổ chức đích (Sẽ được CẬP NHẬT thông tin)"
            required
          >
            <Select
              placeholder="Chọn tổ chức đích..."
              value={targetId}
              onChange={(val) => setTargetId(val)}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={orgs.map((o) => ({
                value: o.id,
                label: `${o.name} (MST: ${o.tax_code || 'chưa có'})`
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
