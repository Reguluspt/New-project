import React, { useEffect } from 'react';
import { Modal, Form, Input, Select, message } from 'antd';
import { updateSoboRecord } from '../../api/sobo';

export default function SoboEditModal({ open, record, onOk, onCancel }) {
  const [form] = Form.useForm();

  useEffect(() => {
    if (record) {
      form.setFieldsValue({
        asset_type: record.asset_type || 'real_estate',
        dia_chi: record.dia_chi || '',
        so_thua: record.so_thua || '',
        so_to: record.so_to || '',
        link: record.link || '',
        email_recipient: record.email_recipient || '',
        status: record.status || 'PENDING',
        note: record.note || '',
        equipment_name: record.equipment_name || '',
      });
    } else {
      form.resetFields();
    }
  }, [record, form, open]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await updateSoboRecord(record.id, values);
      message.success('Cập nhật hồ sơ sơ bộ thành công');
      onOk();
    } catch (error) {
      if (error.name !== 'ValidationError') {
        message.error('Lỗi khi cập nhật hồ sơ: ' + (error.response?.data?.error || error.message));
      }
    }
  };

  return (
    <Modal
      title={`Chỉnh sửa Hồ sơ Sơ bộ #${record?.id}`}
      open={open}
      onOk={handleSubmit}
      onCancel={onCancel}
      destroyOnClose
      okText="Lưu thay đổi"
      cancelText="Hủy"
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ asset_type: 'real_estate', status: 'PENDING' }}
        style={{ marginTop: 16 }}
      >
        <Form.Item
          name="asset_type"
          label="Loại tài sản"
          rules={[{ required: true, message: 'Vui lòng chọn loại tài sản' }]}
        >
          <Select>
            <Select.Option value="real_estate">🏠 Bất động sản</Select.Option>
            <Select.Option value="machinery">⚙️ Máy móc thiết bị</Select.Option>
          </Select>
        </Form.Item>

        {/* Dynamic field based on asset_type */}
        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.asset_type !== curr.asset_type}>
          {({ getFieldValue }) => {
            const isMachinery = getFieldValue('asset_type') === 'machinery';
            return isMachinery ? (
              <Form.Item
                name="equipment_name"
                label="Tên thiết bị"
                rules={[{ required: true, message: 'Vui lòng nhập tên thiết bị' }]}
              >
                <Input placeholder="Ví dụ: Dây chuyền sản xuất bao bì" />
              </Form.Item>
            ) : (
              <div style={{ display: 'flex', gap: 16 }}>
                <Form.Item name="so_thua" label="Số thửa" style={{ flex: 1 }}>
                  <Input placeholder="Ví dụ: 123" />
                </Form.Item>
                <Form.Item name="so_to" label="Số tờ" style={{ flex: 1 }}>
                  <Input placeholder="Ví dụ: 45" />
                </Form.Item>
              </div>
            );
          }}
        </Form.Item>

        <Form.Item
          name="dia_chi"
          label="Địa chỉ tài sản"
          rules={[{ required: true, message: 'Vui lòng nhập địa chỉ tài sản' }]}
        >
          <Input placeholder="Nhập địa chỉ chi tiết hoặc thửa đất" />
        </Form.Item>

        <Form.Item name="link" label="Đường dẫn bản đồ (Google Map / Location Link)">
          <Input placeholder="https://maps.google.com/..." />
        </Form.Item>

        <Form.Item
          name="email_recipient"
          label="Email người nhận / Chuyên viên xử lý sơ bộ"
          rules={[{ required: true, type: 'email', message: 'Vui lòng nhập email hợp lệ' }]}
        >
          <Input placeholder="nghiepvu@cenvalue.vn" />
        </Form.Item>

        <Form.Item
          name="status"
          label="Trạng thái phản hồi"
          rules={[{ required: true }]}
        >
          <Select>
            <Select.Option value="PENDING">🔴 Chờ phản hồi</Select.Option>
            <Select.Option value="RESPONDED">🟢 Đã phản hồi</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item name="note" label="Ghi chú nội bộ">
          <Input.TextArea rows={3} placeholder="Ghi chú về kết quả khảo sát, phản hồi sơ bộ..." />
        </Form.Item>
      </Form>
    </Modal>
  );
}
