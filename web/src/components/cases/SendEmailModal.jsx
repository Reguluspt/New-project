import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Checkbox, Space, Button, message } from 'antd';
import { MailOutlined, FileOutlined } from '@ant-design/icons';
import { sendEmail } from '../../api/documents';

export default function SendEmailModal({ open, onClose, caseId, documents, initialSubject, initialBody }) {
  const [form] = Form.useForm();
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (open) {
      // Set defaults
      form.setFieldsValue({
        recipients: [],
        cc: [],
        subject: initialSubject || `Kết quả thẩm định - Hồ sơ #${caseId}`,
        body: initialBody || 'Kính gửi Quý khách hàng,\n\nChúng tôi xin gửi tài liệu thẩm định đính kèm bên dưới.\n\nTrân trọng,\nCentury Appraisal',
        attachments: documents ? documents.map(d => d.name) : []
      });
    }
  }, [open, caseId, documents, initialSubject, initialBody, form]);

  const handleSubmit = async (values) => {
    setSending(true);
    try {
      const payload = {
        recipients: values.recipients,
        cc: values.cc || [],
        subject: values.subject,
        body: values.body.replace(/\n/g, '<br>'), // Simple newline to HTML converter
        attachments: values.attachments,
        send_method: 'oauth2'
      };
      
      await sendEmail(caseId, payload);
      message.success('Gửi email thành công! 📬');
      onClose();
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Gửi email thất bại');
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal
      open={open}
      title={
        <Space>
          <MailOutlined style={{ color: '#0f6cbd' }} />
          <span>Gửi email kết quả thẩm định</span>
        </Space>
      }
      okText="Gửi mail"
      cancelText="Hủy"
      confirmLoading={sending}
      onCancel={onClose}
      onOk={() => form.submit()}
      width={680}
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
          name="recipients"
          label="Người nhận (To)"
          rules={[{ required: true, message: 'Vui lòng nhập ít nhất một email người nhận' }]}
        >
          <Select 
            mode="tags" 
            placeholder="Nhập email và ấn Enter..." 
            style={{ width: '100%' }}
            tokenSeparators={[',', ' ']}
          />
        </Form.Item>

        <Form.Item
          name="cc"
          label="Đồng gửi (CC)"
        >
          <Select 
            mode="tags" 
            placeholder="Nhập email đồng gửi..." 
            style={{ width: '100%' }}
            tokenSeparators={[',', ' ']}
          />
        </Form.Item>

        <Form.Item
          name="subject"
          label="Tiêu đề email"
          rules={[{ required: true, message: 'Vui lòng nhập tiêu đề email' }]}
        >
          <Input placeholder="Nhập tiêu đề..." />
        </Form.Item>

        <Form.Item
          name="body"
          label="Nội dung"
          rules={[{ required: true, message: 'Vui lòng nhập nội dung email' }]}
        >
          <Input.TextArea 
            rows={8} 
            placeholder="Kính gửi..." 
            style={{ fontFamily: 'Segoe UI, Helvetica, sans-serif' }}
          />
        </Form.Item>

        {documents && documents.length > 0 && (
          <Form.Item
            name="attachments"
            label="Tài liệu đính kèm"
            valuePropName="value"
          >
            <Checkbox.Group style={{ width: '100%' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {documents.map((doc) => (
                  <Checkbox key={doc.name} value={doc.name} style={{ display: 'flex', alignItems: 'center' }}>
                    <Space size="small">
                      <FileOutlined style={{ color: doc.type === 'pdf' ? '#ef4444' : '#0f6cbd' }} />
                      <span>{doc.name}</span>
                      <span style={{ color: '#8c8c8c', fontSize: 12 }}>
                        ({(doc.size / 1024).toFixed(1)} KB)
                      </span>
                    </Space>
                  </Checkbox>
                ))}
              </Space>
            </Checkbox.Group>
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}
