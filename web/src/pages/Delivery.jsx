import React, { useState, useEffect, useRef, useCallback, useContext } from 'react';
import {
  Card,
  Typography,
  Table,
  Button,
  Input,
  Space,
  Form,
  Popconfirm,
  Row,
  Col,
  Statistic,
  message,
  Divider
} from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  SaveOutlined,
  DeleteOutlined,
  ContactsOutlined
} from '@ant-design/icons';
import {
  getDeliveryContacts,
  createDeliveryContact,
  updateDeliveryContact,
  deleteDeliveryContact
} from '../api/delivery';

const { Title, Paragraph } = Typography;

const EditableContext = React.createContext(null);

const EditableRow = ({ index, ...props }) => {
  const [form] = Form.useForm();
  return (
    <Form form={form} component={false}>
      <EditableContext.Provider value={form}>
        <tr {...props} />
      </EditableContext.Provider>
    </Form>
  );
};

const EditableCell = ({
  title,
  editable,
  children,
  dataIndex,
  record,
  handleSave,
  ...restProps
}) => {
  const [editing, setEditing] = useState(false);
  const inputRef = useRef(null);
  const form = useContext(EditableContext);

  useEffect(() => {
    if (editing) {
      inputRef.current.focus();
    }
  }, [editing]);

  const toggleEdit = () => {
    setEditing(!editing);
    form.setFieldsValue({
      [dataIndex]: record[dataIndex],
    });
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      toggleEdit();
      handleSave({ ...record, ...values });
    } catch (errInfo) {
      console.log('Save failed:', errInfo);
    }
  };

  let childNode = children;

  if (editable) {
    childNode = editing ? (
      <Form.Item
        name={dataIndex}
        style={{ margin: 0 }}
        rules={[
          {
            required: true,
            message: `${title} là bắt buộc.`,
          },
        ]}
      >
        {dataIndex === 'full_details' ? (
          <Input.TextArea
            ref={inputRef}
            onBlur={save}
            autoSize={{ minRows: 2, maxRows: 6 }}
            style={{ width: '100%' }}
          />
        ) : (
          <Input
            ref={inputRef}
            onPressEnter={save}
            onBlur={save}
          />
        )}
      </Form.Item>
    ) : (
      <div
        className="editable-cell-value-wrap"
        style={{
          padding: '4px 12px',
          minHeight: '32px',
          border: '1px solid transparent',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.2s'
        }}
        onClick={toggleEdit}
        onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#d9d9d9'; }}
        onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'transparent'; }}
      >
        <span style={{ whiteSpace: 'pre-wrap' }}>{children}</span>
      </div>
    );
  }

  return <td {...restProps}>{childNode}</td>;
};

export default function Delivery() {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  // Fetch delivery contacts
  const fetchContacts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getDeliveryContacts({ search: search.trim() });
      setContacts(res.data || []);
    } catch (err) {
      console.error(err);
      message.error('Không thể tải danh sách liên hệ chuyển phát');
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  // Inline cell save
  const handleCellSave = async (row) => {
    const hide = message.loading('Đang cập nhật...', 0);
    try {
      await updateDeliveryContact(row.id, {
        short_name: row.short_name,
        full_details: row.full_details
      });
      message.success('Đã cập nhật liên hệ chuyển phát');
      fetchContacts();
    } catch (err) {
      message.error('Lỗi cập nhật: ' + (err.response?.data?.error || err.message));
    } finally {
      hide();
    }
  };

  // Add row
  const handleAddRow = async () => {
    const hide = message.loading('Đang tạo liên hệ mới...', 0);
    try {
      const newContact = {
        short_name: 'Liên hệ mới ' + (contacts.length + 1),
        full_details: 'Họ tên người nhận\nĐịa chỉ cụ thể\nSố điện thoại'
      };
      await createDeliveryContact(newContact);
      message.success('Đã thêm một liên hệ mới. Hãy click vào ô để chỉnh sửa.');
      fetchContacts();
    } catch (err) {
      message.error('Lỗi thêm dòng mới: ' + (err.response?.data?.error || err.message));
    } finally {
      hide();
    }
  };

  // Delete contact
  const handleDelete = async (id) => {
    try {
      await deleteDeliveryContact(id);
      message.success('Đã xóa liên hệ thành công');
      fetchContacts();
    } catch (err) {
      message.error('Lỗi xóa liên hệ: ' + (err.response?.data?.error || err.message));
    }
  };

  const defaultColumns = [
    {
      title: 'Tên viết tắt / Tên gợi nhớ',
      dataIndex: 'short_name',
      width: '25%',
      editable: true,
      sorter: (a, b) => a.short_name.localeCompare(b.short_name),
      render: (text) => <strong>{text}</strong>
    },
    {
      title: 'Thông tin chi tiết người nhận (Tên, Địa chỉ, Số điện thoại)',
      dataIndex: 'full_details',
      width: '60%',
      editable: true,
    },
    {
      title: 'Thao tác',
      key: 'actions',
      width: '15%',
      render: (_, record) => (
        <Popconfirm
          title="Xóa liên hệ"
          description="Bạn chắc chắn muốn xóa liên hệ này khỏi danh bạ?"
          onConfirm={() => handleDelete(record.id)}
          okText="Xóa"
          cancelText="Hủy"
          okButtonProps={{ danger: true }}
        >
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
          >
            Xóa
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const columns = defaultColumns.map((col) => {
    if (!col.editable) {
      return col;
    }
    return {
      ...col,
      onCell: (record) => ({
        record,
        editable: col.editable,
        dataIndex: col.dataIndex,
        title: col.title,
        handleSave: handleCellSave,
      }),
    };
  });

  const components = {
    body: {
      row: EditableRow,
      cell: EditableCell,
    },
  };

  const totalContacts = contacts.length;
  const completeContacts = contacts.filter(
    (c) => c.short_name && c.full_details && c.full_details.split('\n').length >= 2
  ).length;
  const incompleteContacts = Math.max(totalContacts - completeContacts, 0);

  return (
    <div>
      {/* Title Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0, fontWeight: 700 }}>
          📦 Danh bạ chuyển phát
        </Title>
        <Paragraph style={{ color: '#64748b', margin: '4px 0 0 0' }}>
          Quản lý người nhận hồ sơ phát hành chứng thư, địa chỉ, điện thoại và nội dung dùng khi gửi mail chuyển phát.
        </Paragraph>
      </div>

      {/* KPI Stats cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card bordered style={{ borderLeft: '5px solid #007f7a' }} hoverable>
            <Statistic title="Tổng liên hệ" value={totalContacts} prefix={<ContactsOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card bordered style={{ borderLeft: '5px solid #047857' }} hoverable>
            <Statistic title="Liên hệ đầy đủ thông tin" value={completeContacts} suffix={`/ ${totalContacts}`} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card bordered style={{ borderLeft: '5px solid #c2413d' }} hoverable>
            <Statistic title="Cần bổ sung thông tin" value={incompleteContacts} />
          </Card>
        </Col>
      </Row>

      {/* Main Table Card */}
      <Card
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <span>Bảng chỉnh sửa danh bạ chuyển phát</span>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddRow}
            >
              Tạo danh bạ mới
            </Button>
          </div>
        }
      >
        <Input
          placeholder="🔍 Tìm nhanh người nhận, tên gợi nhớ, địa chỉ..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ marginBottom: 16 }}
          allowClear
          prefix={<SearchOutlined style={{ color: '#94a3b8' }} />}
        />
        
        <Table
          components={components}
          rowClassName={() => 'editable-row'}
          bordered
          dataSource={contacts}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          size="middle"
        />

        <Divider />
        <Paragraph style={{ color: '#64748b', fontSize: '13px' }}>
          💡 <strong>Hướng dẫn chỉnh sửa nhanh:</strong>
          <ol style={{ marginTop: 4, paddingLeft: 20 }}>
            <li>Rê chuột vào ô <strong>Tên gợi nhớ</strong> hoặc <strong>Thông tin chi tiết</strong>.</li>
            <li>Click chuột vào ô để mở trình chỉnh sửa nội dung.</li>
            <li>Sau khi chỉnh sửa xong, click chuột ra ngoài (blur) hoặc nhấn phím <strong>Enter</strong> (đối với tên gợi nhớ) để lưu tự động.</li>
            <li>Thông tin chi tiết nên gồm đầy đủ: Tên người nhận, Địa chỉ cụ thể, Số điện thoại liên hệ (mỗi thông tin trên một dòng).</li>
          </ol>
        </Paragraph>
      </Card>
    </div>
  );
}
