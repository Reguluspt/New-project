import React, { useEffect, useState } from 'react';
import { DatePicker, Form, Input, Modal, Select, Switch, message } from 'antd';
import dayjs from 'dayjs';

import client from '../../api/client';

const { TextArea } = Input;

const priorityOptions = [
  { value: 'low', label: 'Thấp' },
  { value: 'medium', label: 'Trung bình' },
  { value: 'high', label: 'Cao' },
];

function toDateValue(value) {
  return value ? dayjs(value) : null;
}

function toApiDate(value) {
  return value ? value.format('YYYY-MM-DD HH:mm:ss') : null;
}

function compactText(value, fallback = 'Chưa có') {
  return value || fallback;
}

function buildCaseOption(item) {
  const contractNumber = compactText(item.contract_number, `Hồ sơ #${item.id}`);
  const customerInfo = compactText(item.customer_info);
  const source = compactText(item.source, '');
  const note = compactText(item.personal_note, '');
  const assetDescription = compactText(item.asset_description, '');
  const status = compactText(item.case_status, '');

  const searchText = [
    item.id,
    contractNumber,
    customerInfo,
    source,
    note,
    assetDescription,
  ].filter(Boolean).join(' ').toLowerCase();

  return {
    value: item.id,
    searchText,
    label: (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '4px 0', borderBottom: '1px solid #f0f0f0', paddingBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <strong style={{ fontSize: 14 }}>{contractNumber}</strong>
            <span style={{ fontSize: 12, fontWeight: 500, color: status === 'Hủy' ? '#ef4444' : status === 'Hoàn thành' ? '#22c55e' : '#eab308' }}>{status}</span>
        </div>
        <span style={{ color: '#334155', fontSize: 13 }}><strong>Khách:</strong> {customerInfo}</span>
        {assetDescription && <span style={{ color: '#475569', fontSize: 12 }}><strong>Tài sản:</strong> {assetDescription}</span>}
        <span style={{ color: '#64748b', fontSize: 12, marginTop: 2 }}>
          {[source && `Nguồn: ${source}`, note && `Ghi chú: ${note}`]
            .filter(Boolean)
            .join(' • ')}
        </span>
      </div>
    ),
  };
}

export default function TaskModal({ open, task, defaultCaseId, onCancel, onSubmit }) {
  const [form] = Form.useForm();
  const [caseOptions, setCaseOptions] = useState([]);
  const [loadingCases, setLoadingCases] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const reminderEnabled = Form.useWatch('reminder_enabled', form);
  const isEdit = !!task?.id;

  useEffect(() => {
    if (!open) return;

    form.setFieldsValue({
      title: task?.title || '',
      description: task?.description || '',
      priority: task?.priority || 'medium',
      due_date: toDateValue(task?.due_date),
      case_id: task?.case_id ?? defaultCaseId ?? undefined,
      reminder_enabled: false,
      remind_at: null,
    });
  }, [defaultCaseId, form, open, task]);

  useEffect(() => {
    if (!open) return;

    setLoadingCases(true);
    client.get('/cases', { params: { page: 1, size: 500 } })
      .then((response) => {
        const cases = response.data?.items || [];
        setCaseOptions(cases.map(buildCaseOption));
      })
      .catch((error) => {
        console.error('Không thể tải danh sách hồ sơ', error);
        message.error('Không thể tải danh sách hồ sơ');
      })
      .finally(() => setLoadingCases(false));
  }, [open]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const payload = {
        title: values.title.trim(),
        description: values.description || '',
        priority: values.priority,
        due_date: toApiDate(values.due_date),
        case_id: values.case_id ?? null,
      };

      if (values.reminder_enabled && values.remind_at) {
        payload.reminder = {
          remind_at: toApiDate(values.remind_at),
          channels: 'telegram',
        };
      }

      await onSubmit(payload);
      form.resetFields();
    } catch (error) {
      if (error?.errorFields) return;
      console.error('Không thể lưu công việc', error);
      message.error(error?.response?.data?.error || 'Không thể lưu công việc');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      title={isEdit ? 'Chỉnh sửa công việc' : 'Tạo công việc mới'}
      open={open}
      onCancel={onCancel}
      onOk={handleOk}
      confirmLoading={submitting}
      okText={isEdit ? 'Lưu' : 'Tạo'}
      cancelText="Hủy"
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="title"
          label="Tiêu đề"
          rules={[{ required: true, message: 'Vui lòng nhập tiêu đề công việc' }]}
        >
          <Input placeholder="Nhập tiêu đề công việc" />
        </Form.Item>

        <Form.Item name="description" label="Mô tả chi tiết">
          <TextArea rows={4} placeholder="Nhập mô tả chi tiết" />
        </Form.Item>

        <Form.Item name="priority" label="Mức độ ưu tiên">
          <Select options={priorityOptions} />
        </Form.Item>

        <Form.Item name="due_date" label="Ngày đến hạn">
          <DatePicker showTime style={{ width: '100%' }} format="DD/MM/YYYY HH:mm" />
        </Form.Item>

        <Form.Item name="case_id" label="Liên kết hồ sơ thẩm định">
          <Select
            allowClear
            showSearch
            loading={loadingCases}
            filterOption={(input, option) => (
              option?.searchText || ''
            ).includes(input.trim().toLowerCase())}
            options={caseOptions}
            placeholder="Tìm theo số hợp đồng, khách hàng, tài sản, ghi chú, nguồn"
          />
        </Form.Item>

        <Form.Item
          name="reminder_enabled"
          label="Hẹn giờ nhắc việc qua Telegram"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        {reminderEnabled ? (
          <Form.Item
            name="remind_at"
            label="Thời điểm nhắc việc"
            rules={[{ required: true, message: 'Vui lòng chọn thời điểm nhắc việc' }]}
          >
            <DatePicker showTime style={{ width: '100%' }} format="DD/MM/YYYY HH:mm" />
          </Form.Item>
        ) : null}
      </Form>
    </Modal>
  );
}
