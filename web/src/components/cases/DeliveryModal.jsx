import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Checkbox, Radio, Space, Button, message } from 'antd';
import { SendOutlined, CompassOutlined } from '@ant-design/icons';
import { getDeliveryContacts, saveDelivery, sendPhathanhReply } from '../../api/documents';

export default function DeliveryModal({ open, onClose, caseId, onSuccess }) {
  const [form] = Form.useForm();
  const [contacts, setContacts] = useState([]);
  const [loadingContacts, setLoadingContacts] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [sourceType, setSourceType] = useState('select'); // 'select' | 'manual'

  useEffect(() => {
    if (open) {
      fetchContacts();
      form.setFieldsValue({
        source: 'select',
        certificate_number: '',
        tracking_number: '',
        delivery_contact_id: undefined,
        manual_short_name: '',
        manual_details: '',
        save_to_contacts: false
      });
      setSourceType('select');
    }
  }, [open, form]);

  const fetchContacts = async () => {
    setLoadingContacts(true);
    try {
      const res = await getDeliveryContacts();
      setContacts(res.data || []);
    } catch (err) {
      console.error(err);
      message.error('Không thể tải danh bạ chuyển phát');
    } finally {
      setLoadingContacts(false);
    }
  };

  const handleSourceChange = (e) => {
    setSourceType(e.target.value);
  };

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      let recipientText = '';
      let selectedContactId = values.delivery_contact_id;

      if (sourceType === 'select') {
        const selectedContact = contacts.find(c => c.id === values.delivery_contact_id);
        recipientText = selectedContact ? selectedContact.full_details : 'VP Gia Lai (mặc định)';
      } else {
        recipientText = values.manual_details;
        // If manual and "save to contacts" is checked, we can create a contact.
        // Wait, the backend save-delivery endpoint can save contact if save_to_contacts is true.
        // But for simplicity, we can pass it or handle it in backend.
        // Our backend save_case_delivery handles delivery_contact_id.
      }

      // 1. Save delivery details (contact + tracking number)
      await saveDelivery(caseId, {
        delivery_contact_id: selectedContactId,
        tracking_number: values.tracking_number,
        // Send manual details if manual
        manual_short_name: values.manual_short_name,
        manual_details: values.manual_details,
        save_to_contacts: values.save_to_contacts
      });

      // 2. Send the certificate reply email
      const replyRes = await sendPhathanhReply(caseId, {
        certificate_number: values.certificate_number,
        recipient: recipientText
      });

      message.success(`Đã gửi mail phát hành chứng thư thành công tới ${replyRes.data?.to_email || 'người nhận'}!`);
      
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Gửi mail phát hành hoặc lưu thông tin thất bại');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      title={
        <Space>
          <CompassOutlined style={{ color: '#0f6cbd' }} />
          <span>Phát hành chứng thư & Thông tin chuyển phát</span>
        </Space>
      }
      okText="Xác nhận phát hành"
      cancelText="Hủy"
      confirmLoading={submitting}
      onCancel={onClose}
      onOk={() => form.submit()}
      width={600}
      destroyOnClose
      style={{ borderRadius: 10 }}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        style={{ marginTop: 16 }}
      >
        <Form.Item
          name="certificate_number"
          label="Số chứng thư phát hành"
          rules={[{ required: true, message: 'Vui lòng nhập số chứng thư' }]}
        >
          <Input placeholder="Ví dụ: CT-010/2026/CEN-GL" />
        </Form.Item>

        <Form.Item
          name="tracking_number"
          label="Mã vận đơn chuyển phát"
        >
          <Input placeholder="Nhập mã vận đơn (EMS, ViettelPost, etc.) nếu có" />
        </Form.Item>

        <Form.Item label="Nguồn thông tin người nhận">
          <Radio.Group onChange={handleSourceChange} value={sourceType}>
            <Radio value="select">Chọn từ danh bạ</Radio>
            <Radio value="manual">Nhập thủ công</Radio>
          </Radio.Group>
        </Form.Item>

        {sourceType === 'select' ? (
          <Form.Item
            name="delivery_contact_id"
            label="Chọn người nhận chuyển phát"
            rules={[{ required: true, message: 'Vui lòng chọn người nhận chuyển phát' }]}
          >
            <Select
              placeholder="Chọn từ danh bạ..."
              loading={loadingContacts}
              style={{ width: '100%' }}
              options={[
                { value: 0, label: 'VP Gia Lai (mặc định) - 90/60/3 Trường Chinh' },
                ...contacts.map(c => ({
                  value: c.id,
                  label: `${c.short_name} (${c.full_details.split('\n')[0] || ''})`
                }))
              ]}
            />
          </Form.Item>
        ) : (
          <>
            <Form.Item
              name="manual_short_name"
              label="Tên gợi nhớ (Tên ngắn)"
              help="Cần thiết khi lưu người nhận này vào danh bạ."
            >
              <Input placeholder="Ví dụ: VP Kon Tum" />
            </Form.Item>

            <Form.Item
              name="manual_details"
              label="Thông tin người nhận chi tiết"
              rules={[{ required: true, message: 'Vui lòng nhập chi tiết người nhận' }]}
            >
              <Input.TextArea
                rows={4}
                placeholder="Họ tên người nhận hoặc đơn vị&#10;Địa chỉ: ...&#10;Điện thoại: ..."
              />
            </Form.Item>

            <Form.Item name="save_to_contacts" valuePropName="checked">
              <Checkbox>Lưu người nhận này vào danh bạ chuyển phát</Checkbox>
            </Form.Item>
          </>
        )}
      </Form>
    </Modal>
  );
}
