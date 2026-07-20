import React, { useEffect, useMemo, useState } from 'react';
import { Modal, Form, Input, Select, Checkbox, Radio, Space, Button, message, Divider, Typography } from 'antd';
import { CompassOutlined, PlusOutlined } from '@ant-design/icons';
import { createDeliveryContact, getDeliveryContacts, saveDelivery, sendPhathanhReply } from '../../api/documents';
import { deliveryMailFailureNotice } from './deliveryMailError';

const DEFAULT_CONTACT_DETAILS = 'CÔNG TY CỔ PHẦN THẨM ĐỊNH GIÁ THẾ KỶ - VP TẠI GIA LAI\nĐịa chỉ: 90/60/3 Trường Chinh, TP. Pleiku, Gia Lai\nĐiện thoại: 0905226968';

export default function DeliveryModal({ open, onClose, caseId, contractNumber, onSuccess }) {
  const [form] = Form.useForm();
  const [contactForm] = Form.useForm();
  const [contacts, setContacts] = useState([]);
  const [loadingContacts, setLoadingContacts] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [sourceType, setSourceType] = useState('select');
  const [contactModalOpen, setContactModalOpen] = useState(false);
  const [savingContact, setSavingContact] = useState(false);
  const [contactSearch, setContactSearch] = useState('');

  const selectedContactId = Form.useWatch('delivery_contact_id', form);
  const manualDetails = Form.useWatch('manual_details', form);

  useEffect(() => {
    if (open) {
      fetchContacts();
      form.setFieldsValue({
        source: 'select',
        delivery_contact_id: undefined,
        manual_short_name: '',
        manual_details: '',
        save_to_contacts: false,
      });
      setSourceType('select');
      setContactSearch('');
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

  const selectedContactDetails = useMemo(() => {
    if (sourceType === 'manual') {
      return manualDetails || '';
    }
    if (selectedContactId === 0) {
      return DEFAULT_CONTACT_DETAILS;
    }
    const selectedContact = contacts.find((contact) => contact.id === selectedContactId);
    return selectedContact?.full_details || '';
  }, [contacts, manualDetails, selectedContactId, sourceType]);

  const handleSourceChange = (e) => {
    setSourceType(e.target.value);
  };

  const handleAddContact = async () => {
    try {
      const values = await contactForm.validateFields();
      setSavingContact(true);
      const res = await createDeliveryContact({
        short_name: values.short_name,
        full_details: values.full_details,
      });
      await fetchContacts();
      if (res.data?.id) {
        form.setFieldValue('delivery_contact_id', res.data.id);
      }
      setContactModalOpen(false);
      contactForm.resetFields();
      message.success('Đã thêm người nhận vào danh bạ chuyển phát');
    } catch (err) {
      if (err?.errorFields) return;
      console.error(err);
      message.error(err.response?.data?.error || 'Không thể thêm danh bạ chuyển phát');
    } finally {
      setSavingContact(false);
    }
  };

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      const certificateNumber = String(contractNumber || '').trim();
      if (!certificateNumber) {
        message.error('Hồ sơ chưa có số hợp đồng để dùng làm số chứng thư');
        return;
      }

      let recipientText = '';
      let selectedContactIdForSave = values.delivery_contact_id;

      if (sourceType === 'select') {
        recipientText = selectedContactDetails || DEFAULT_CONTACT_DETAILS;
      } else {
        recipientText = values.manual_details;
        selectedContactIdForSave = null;
      }

      let deliverySaveWarning = '';
      try {
        await saveDelivery(caseId, {
          delivery_contact_id: selectedContactIdForSave,
          manual_short_name: values.manual_short_name,
          manual_details: values.manual_details,
          save_to_contacts: values.save_to_contacts,
        });
      } catch (saveErr) {
        console.error(saveErr);
        deliverySaveWarning = 'Không lưu được thông tin chuyển phát, nhưng hệ thống vẫn tiếp tục gửi mail phát hành.';
      }

      const replyRes = await sendPhathanhReply(caseId, {
        certificate_number: certificateNumber,
        recipient: recipientText,
      });

      const resultWarnings = [deliverySaveWarning, replyRes.data?.warning].filter(Boolean);
      Modal.success({
        title: 'Gửi mail phát hành chứng thư thành công',
        content: (
          <div>
            <p>
              Đã gửi mail phát hành chứng thư tới{' '}
              <strong>{replyRes.data?.to_email || 'người nhận'}</strong>.
            </p>
            {resultWarnings.map((warning) => (
              <p key={warning} style={{ marginBottom: 0, color: '#b45309' }}>
                {warning}
              </p>
            ))}
          </div>
        ),
        okText: 'Đóng',
        onOk: () => {
          if (onSuccess) onSuccess();
          onClose();
        },
      });
    } catch (err) {
      console.error(err);
      const failureNotice = deliveryMailFailureNotice(err);
      Modal[failureNotice.type]({
        title: failureNotice.title,
        content: failureNotice.content,
        okText: 'Đóng',
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Modal
        open={open}
        title={(
          <Space>
            <CompassOutlined style={{ color: '#007f7a' }} />
            <span>Phát hành chứng thư & Thông tin chuyển phát</span>
          </Space>
        )}
        okText="Xác nhận phát hành"
        cancelText="Hủy"
        confirmLoading={submitting}
        onCancel={onClose}
        onOk={() => form.submit()}
        width={600}
        destroyOnClose
        style={{ borderRadius: 10 }}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 16 }}>
          <Form.Item label="Số chứng thư phát hành">
            <Input value={contractNumber || ''} disabled />
          </Form.Item>

          <Form.Item label="Nguồn thông tin người nhận">
            <Radio.Group onChange={handleSourceChange} value={sourceType}>
              <Radio value="select">Chọn từ danh bạ</Radio>
              <Radio value="manual">Nhập thủ công</Radio>
            </Radio.Group>
          </Form.Item>

          {sourceType === 'select' ? (
            <>
              <Form.Item
                name="delivery_contact_id"
                label="Chọn người nhận chuyển phát"
                rules={[{ required: true, message: 'Vui lòng chọn người nhận chuyển phát' }]}
              >
                <Select
                  placeholder="Chọn từ danh bạ..."
                  loading={loadingContacts}
                  showSearch
                  searchValue={contactSearch}
                  onSearch={setContactSearch}
                  onDropdownOpenChange={(visible) => {
                    if (visible) setContactSearch('');
                  }}
                  optionFilterProp="label"
                  filterOption={(input, option) =>
                    String(option?.label || '').toLowerCase().includes(input.toLowerCase())
                  }
                  style={{ width: '100%' }}
                  dropdownRender={(menu) => (
                    <>
                      {menu}
                      <Divider style={{ margin: '8px 0' }} />
                      <Button
                        type="text"
                        icon={<PlusOutlined />}
                        block
                        onClick={() => setContactModalOpen(true)}
                      >
                        Thêm danh bạ chuyển phát
                      </Button>
                    </>
                  )}
                  options={[
                    { value: 0, label: 'VP Gia Lai (mặc định) - 90/60/3 Trường Chinh' },
                    ...contacts.map((contact) => ({
                      value: contact.id,
                      label: `${contact.short_name} (${contact.full_details.split('\n')[0] || ''})`,
                    })),
                  ]}
                />
              </Form.Item>

              <Form.Item label="Thông tin chuyển phát">
                <Input.TextArea
                  value={selectedContactDetails}
                  rows={4}
                  readOnly
                  placeholder="Chọn người nhận chuyển phát để kiểm tra thông tin"
                />
              </Form.Item>
            </>
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

          <Typography.Text type="secondary">
            Số chứng thư sẽ lấy theo số hợp đồng của hồ sơ.
          </Typography.Text>
        </Form>
      </Modal>

      <Modal
        open={contactModalOpen}
        title="Thêm danh bạ chuyển phát"
        okText="Lưu danh bạ"
        cancelText="Hủy"
        confirmLoading={savingContact}
        onOk={handleAddContact}
        onCancel={() => {
          setContactModalOpen(false);
          contactForm.resetFields();
        }}
        destroyOnClose
      >
        <Form form={contactForm} layout="vertical">
          <Form.Item
            name="short_name"
            label="Tên gợi nhớ"
            rules={[{ required: true, message: 'Vui lòng nhập tên gợi nhớ' }]}
          >
            <Input placeholder="Ví dụ: BIDV Nam Gia Lai" />
          </Form.Item>

          <Form.Item
            name="full_details"
            label="Thông tin chuyển phát"
            rules={[{ required: true, message: 'Vui lòng nhập thông tin chuyển phát' }]}
          >
            <Input.TextArea
              rows={5}
              placeholder="Họ tên người nhận hoặc đơn vị&#10;Địa chỉ: ...&#10;Điện thoại: ..."
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
