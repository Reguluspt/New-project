import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Space, Button, message, Modal, Drawer, Input, List, Form, Badge, Checkbox, Select, Tooltip } from 'antd';
import { 
  EditOutlined, 
  DeleteOutlined, 
  PlusOutlined, 
  DownloadOutlined, 
  UploadOutlined,
  CommentOutlined,
  FolderOpenOutlined,
  FileWordOutlined,
  InteractionOutlined,
  EyeOutlined,
  SendOutlined,
  GlobalOutlined,
  MailOutlined,
  EnvironmentOutlined,
  BankOutlined,
  CalendarOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useResizableColumns } from '../../hooks/useResizableColumns';
import { 
  listCases, 
  getCase,
  deleteCase, 
  updatePayment, 
  updateStatus,
  getNotes, 
  addNote,
  exportCases 
} from '../../api/cases';
import { generateDocuments, downloadAllZip } from '../../api/documents';
import { sendEmail as sendAppraisalEmail, submitWeb } from '../../api/entry';
import CaseFilterBar from './CaseFilterBar';
import CaseEditModal from './CaseEditModal';
import CaseImportModal from './CaseImportModal';
import DeliveryModal from './DeliveryModal';

export default function CaseTable({ filterOptions, onFilterOptionsRefresh }) {
  const navigate = useNavigate();
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  
  // Query parameters state
  const [filters, setFilters] = useState({
    page: 1,
    size: 15,
    sort: 'id',
    order: 'desc',
    search: '',
    status: '',
    branch: '',
    valuation_branch: '',
    appraiser_name: '',
    execution_month: '',
    payment_status: ''
  });

  // Modal / Drawer control states
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingCase, setEditingCase] = useState(null);
  
  const [importModalOpen, setImportModalOpen] = useState(false);
  
  const [notesDrawerOpen, setNotesDrawerOpen] = useState(false);
  const [activeCaseForNotes, setActiveCaseForNotes] = useState(null);
  const [notesList, setNotesList] = useState([]);
  const [newNoteText, setNewNoteText] = useState('');
  const [addingNote, setAddingNote] = useState(false);

  // Quick Actions modal states
  const [appraisalMailOpen, setAppraisalMailOpen] = useState(false);
  const [activeCaseForAppraisalMail, setActiveCaseForAppraisalMail] = useState(null);
  const [sendingAppraisalMail, setSendingAppraisalMail] = useState(false);
  const [appraisalMailForm] = Form.useForm();

  const [deliveryOpen, setDeliveryOpen] = useState(false);
  const [activeCaseForDelivery, setActiveCaseForDelivery] = useState(null);

  // 1. Quick Word Export
  const handleQuickExportWord = async (record) => {
    const hide = message.loading('Đang xuất nhanh bộ hồ sơ Word...', 0);
    try {
      await generateDocuments(record.id);
      message.success('Xuất hồ sơ Word thành công! Đang tải về...');
      // Download all documents ZIP
      const response = await downloadAllZip(record.id);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `hoso_word_${record.contract_number || record.id}.zip`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Xuất hồ sơ Word thất bại.');
    } finally {
      hide();
    }
  };

  // 2. Open the appraisal-request mail dialog used by the legacy workflow.
  const handleOpenAppraisalMail = (record) => {
    setActiveCaseForAppraisalMail(record);
    appraisalMailForm.setFieldsValue({
      professional_forward_enabled: true,
      professional_recipient_email: 'Kietna@cenvalue.vn',
    });
    setAppraisalMailOpen(true);
  };

  const handleSendAppraisalMail = async () => {
    try {
      const values = await appraisalMailForm.validateFields();
      setSendingAppraisalMail(true);
      const response = await getCase(activeCaseForAppraisalMail.id);
      const caseData = response.data || activeCaseForAppraisalMail;
      const forwardEnabled = values.professional_forward_enabled;

      const result = await sendAppraisalEmail({
        ...caseData,
        professional_forward_enabled: forwardEnabled ? '1' : '0',
        professional_recipient_email: forwardEnabled
          ? values.professional_recipient_email
          : '',
      });

      message.success(`Đã gửi mail yêu cầu định giá tới ${result.data?.to_email || 'người nhận'}.`);
      setAppraisalMailOpen(false);
      setActiveCaseForAppraisalMail(null);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Gửi mail yêu cầu định giá thất bại.');
    } finally {
      setSendingAppraisalMail(false);
    }
  };

  // 3. Open phat hanh email/delivery modal
  const handleOpenDelivery = (record) => {
    setActiveCaseForDelivery(record);
    setDeliveryOpen(true);
  };

  // 4. Submit valuation request to Web automation
  const handleSubmitCaseToWeb = async (record) => {
    const hide = message.loading('Đang gửi yêu cầu định giá lên Web...', 0);
    try {
      const res = await getCase(record.id);
      const caseData = res.data || record;
      
      const payload = {
        ...caseData,
        customer_phone: caseData.customer_phone || '',
        citizen_id: caseData.citizen_id || '',
        personal_note: caseData.personal_note || '',
        advance_payment: caseData.advance_payment ? String(caseData.advance_payment) : '0',
      };
      
      const submitRes = await submitWeb(payload);
      message.success(submitRes.data?.message || 'Gửi yêu cầu lên Web thành công! 🌐');
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Gửi yêu cầu lên Web thất bại.');
    } finally {
      hide();
    }
  };

  // Fetch paginated cases data
  const fetchCases = async () => {
    setLoading(true);
    try {
      const res = await listCases(filters);
      setData(res.data || { items: [], total: 0 });
    } catch (err) {
      message.error(err.response?.data?.error || 'Lấy danh sách hồ sơ thất bại');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [filters]);

  const handleTableChange = (pagination, tableFilters, sorter) => {
    setFilters(prev => ({
      ...prev,
      page: pagination.current,
      size: pagination.pageSize,
      sort: sorter.field || 'id',
      order: sorter.order === 'ascend' ? 'asc' : 'desc'
    }));
  };

  // Toggle Payment status
  const handleTogglePayment = async (record) => {
    const nextStatus = record.payment_status === 'Đã thanh toán' ? 'Chưa thanh toán' : 'Đã thanh toán';
    try {
      await updatePayment(record.id, nextStatus);
      message.success(`Cập nhật trạng thái thanh toán thành công!`);
      fetchCases();
    } catch (err) {
      message.error('Không thể cập nhật trạng thái thanh toán.');
    }
  };

  // Delete case with confirmation dialog
  const handleDelete = (record) => {
    Modal.confirm({
      title: 'Xác nhận xóa hồ sơ',
      content: `Bạn có chắc chắn muốn xóa hồ sơ số "${record.contract_number || 'Chưa có số HĐ'}" của khách hàng "${record.customer_info}"? Hành động này không thể hoàn tác.`,
      okText: 'Xóa',
      okType: 'danger',
      cancelText: 'Hủy',
      onOk: async () => {
        try {
          await deleteCase(record.id);
          message.success('Xóa hồ sơ thành công!');
          fetchCases();
        } catch (err) {
          message.error('Xóa hồ sơ thất bại.');
        }
      }
    });
  };

  // Handle Export Excel
  const handleExport = async () => {
    try {
      message.loading({ content: 'Đang chuẩn bị file Excel...', key: 'exporting' });
      const response = await exportCases(filters);
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `hoso_export_${moment().format('YYYYMMDD')}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      
      message.success({ content: 'Tải file Excel thành công!', key: 'exporting' });
    } catch (err) {
      message.error({ content: 'Xuất file Excel thất bại.', key: 'exporting' });
    }
  };

  // Open Notes Drawer
  const handleOpenNotes = async (record) => {
    setActiveCaseForNotes(record);
    setNotesDrawerOpen(true);
    setNotesList([]);
    try {
      const res = await getNotes(record.id);
      setNotesList(res.data || []);
    } catch (err) {
      message.error('Không thể lấy danh sách ghi chú.');
    }
  };

  // Add a new note
  const handleAddNoteSubmit = async () => {
    if (!newNoteText.trim()) return;
    setAddingNote(true);
    try {
      await addNote(activeCaseForNotes.id, newNoteText.trim());
      message.success('Thêm ghi chú thành công!');
      setNewNoteText('');
      // Refetch notes
      const res = await getNotes(activeCaseForNotes.id);
      setNotesList(res.data || []);
      // Refetch cases table to show changes
      fetchCases();
    } catch (err) {
      message.error('Thêm ghi chú thất bại.');
    } finally {
      setAddingNote(false);
    }
  };

  // Save case (create or update)
  const handleSaveCase = async (values) => {
    try {
      if (editingCase) {
        // Update case
        const { updateCase: apiUpdate } = await import('../../api/cases');
        await apiUpdate(editingCase.id, values);
        message.success('Cập nhật hồ sơ thành công!');
      } else {
        // Create case
        const { createCase: apiCreate } = await import('../../api/cases');
        await apiCreate(values);
        message.success('Thêm hồ sơ mới thành công!');
      }
      setEditModalOpen(false);
      setEditingCase(null);
      fetchCases();
      if (onFilterOptionsRefresh) onFilterOptionsRefresh();
    } catch (err) {
      message.error(err.response?.data?.error || 'Lưu hồ sơ thất bại.');
    }
  };

  const getStatusTag = (status) => {
    switch (status) {
      case 'Hoàn thành':
        return <Tag color="green">Hoàn thành</Tag>;
      case 'Đang thực hiện':
      case 'Đang xử lý':
        return <Tag color="gold">Đang thực hiện</Tag>;
      case 'Đã phát hành':
        return <Tag color="blue">Đã phát hành</Tag>;
      case 'Hủy':
        return <Tag color="red">Hủy</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  const formatDateOnly = (dateStr) => {
    if (!dateStr) return '-';
    try {
      const parts = dateStr.split(' ');
      const datePart = parts[0];
      if (datePart.includes('-')) {
        const bits = datePart.split('-');
        if (bits.length === 3) {
          return `${bits[2]}/${bits[1]}/${bits[0]}`;
        }
      }
      const d = new Date(dateStr);
      if (!isNaN(d.getTime())) {
        const day = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const year = d.getFullYear();
        return `${day}/${month}/${year}`;
      }
    } catch (e) {}
    return dateStr;
  };

  const handleUpdateStatus = async (record, newStatus) => {
    try {
      await updateStatus(record.id, newStatus);
      message.success('Cập nhật trạng thái thành công!');
      fetchCases();
    } catch (err) {
      message.error('Cập nhật trạng thái thất bại.');
    }
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return '-';
    try {
      const normalized = dateStr.replace('T', ' ').split('.')[0];
      const parts = normalized.split(' ');
      const datePart = parts[0];
      const timePart = parts[1] || '';
      
      let formattedDate = datePart;
      if (datePart.includes('-')) {
        const bits = datePart.split('-');
        if (bits.length === 3) {
          formattedDate = `${bits[2]}/${bits[1]}/${bits[0]}`;
        }
      }
      
      if (timePart) {
        return `${timePart} ${formattedDate}`;
      }
      return formattedDate;
    } catch (e) {}
    return dateStr;
  };

  const getStatusStyles = (status) => {
    switch (status) {
      case 'Hoàn thành':
        return {
          bg: '#f0fdf4',
          color: '#16a34a',
          border: '#bbf7d0',
        };
      case 'Hủy':
        return {
          bg: '#fef2f2',
          color: '#dc2626',
          border: '#fecaca',
        };
      case 'Đang xử lý':
      default:
        return {
          bg: '#fffbeb',
          color: '#d97706',
          border: '#fde68a',
        };
    }
  };

  const { getResizableProps } = useResizableColumns('case_list', {
    contract_number: 380,
    personal_note: 200,
    asset_description: 320,
    valuation_fee_number: 110,
    case_status: 140,
    citizen_id: 120,
    actions: 140
  });

  const columns = [
    {
      title: 'HỒ SƠ',
      key: 'contract_number',
      width: 380,
      render: (_, record) => {
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', padding: '2px 0' }}>
            {/* Header: ID & Contract Number & Type Tag */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ 
                fontSize: '11px', 
                color: '#6366f1', 
                backgroundColor: '#e0e7ff', 
                padding: '2px 6px', 
                borderRadius: '4px',
                fontWeight: 700 
              }}>
                #{record.id}
              </span>
              <span style={{ fontSize: '15px', color: '#1e40af', fontWeight: 700, letterSpacing: '-0.01em' }}>
                {record.contract_number || 'N/A'}
              </span>
              {record.customer_type && (
                <Tag color={record.customer_type === 'individual' ? 'purple' : 'blue'} style={{ margin: 0, fontSize: '10px', lineHeight: '16px', height: '18px' }}>
                  {record.customer_type === 'individual' ? 'Cá nhân' : (record.customer_type === 'organization' ? 'Tổ chức' : record.customer_type)}
                </Tag>
              )}
            </div>

            {/* Customer Info */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '13px', color: '#1e293b', fontWeight: 700, textTransform: 'uppercase' }}>
                {record.customer_info || 'N/A'}
              </span>
            </div>

            {/* Metadata list with Monochrome Icons and Labels */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4.5px', fontSize: '13.5px', color: '#475569', marginTop: 2 }}>
              <div style={{ whiteSpace: 'normal', wordBreak: 'break-word', display: 'flex', alignItems: 'flex-start' }}>
                <EnvironmentOutlined style={{ color: '#64748b', marginRight: '6px', marginTop: '3px' }} />
                <span>
                  <span style={{ color: '#475569', fontWeight: 600 }}>Địa chỉ: </span>
                  <span style={{ color: '#0f172a', fontWeight: 'normal' }}>{record.customer_address || '-'}</span>
                </span>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <BankOutlined style={{ color: '#64748b', marginRight: '6px' }} />
                <span>
                  <span style={{ color: '#475569', fontWeight: 600 }}>Nguồn: </span>
                  <span style={{ color: '#0f172a', fontWeight: 'normal' }}>{record.source || '-'}</span>
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center' }}>
                <CalendarOutlined style={{ color: '#64748b', marginRight: '6px' }} />
                <span>
                  <span style={{ color: '#475569', fontWeight: 600 }}>Ngày tạo: </span>
                  <span style={{ color: '#0f172a', fontWeight: 'normal' }}>{formatDateTime(record.created_at)}</span>
                </span>
              </div>

              {record.web_case_id && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: 2 }}>
                  {record.web_case_id.split('\n').map(l => l.trim()).filter(Boolean).map((line, idx) => {
                    const display = line.split(' - ')[0].trim();
                    return (
                      <div 
                        key={idx} 
                        style={{ display: 'inline-flex', alignItems: 'center' }}
                        title={line}
                      >
                        <GlobalOutlined style={{ color: '#0f766e', marginRight: '6px' }} />
                        <span style={{ color: '#0f766e', fontWeight: 800, marginRight: '4px' }}>ID Web: </span>
                        <span style={{ color: '#0d9488', fontWeight: 'normal' }}>{display}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        );
      }
    },
    {
      title: 'GHI CHÚ',
      dataIndex: 'personal_note',
      key: 'personal_note',
      width: 200,
      render: (text) => <div style={{ whiteSpace: 'normal' }}>{text || '•'}</div>
    },
    {
      title: 'TÀI SẢN',
      dataIndex: 'asset_description',
      key: 'asset_description',
      width: 320,
      render: (text) => <div style={{ whiteSpace: 'normal' }}>{text || '-'}</div>
    },
    {
      title: 'PHÍ',
      dataIndex: 'valuation_fee_number',
      key: 'valuation_fee_number',
      align: 'right',
      width: 110,
      render: (val) => val ? val.toLocaleString('vi-VN').replace(/,/g, '.') : '0',
    },
    {
      title: 'TRẠNG THÁI',
      key: 'case_status',
      width: 140,
      align: 'center',
      render: (_, record) => {
        const status = record.case_status || 'Đang xử lý';
        const styles = getStatusStyles(status);
        const isPaid = record.payment_status === 'Đã thanh toán';

        return (
          <div 
            onClick={(e) => e.stopPropagation()} 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '8px', 
              alignItems: 'center',
              padding: '4px 0'
            }}
          >
            <div
              style={{
                backgroundColor: styles.bg,
                border: `1px solid ${styles.border}`,
                borderRadius: '16px',
                padding: '1px 8px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '120px',
                transition: 'all 0.3s ease',
              }}
            >
              <Select 
                value={status} 
                size="small" 
                variant="borderless"
                style={{ 
                  width: '100%', 
                  color: styles.color, 
                  fontWeight: 600,
                  fontSize: '12px',
                  textAlign: 'center',
                }}
                onChange={(newStatus) => handleUpdateStatus(record, newStatus)}
                popupClassName="status-dropdown-popup"
                options={[
                  { value: 'Đang xử lý', label: <span style={{ color: '#d97706', fontWeight: 600 }}>Đang xử lý</span> },
                  { value: 'Hoàn thành', label: <span style={{ color: '#16a34a', fontWeight: 600 }}>Hoàn thành</span> },
                  { value: 'Hủy', label: <span style={{ color: '#dc2626', fontWeight: 600 }}>Hủy</span> },
                ]}
              />
            </div>
            <Button 
              type="text" 
              onClick={() => handleTogglePayment(record)}
              style={{ 
                width: '120px',
                height: '26px',
                borderRadius: '16px',
                backgroundColor: isPaid ? '#e6f7ff' : '#fff1f0',
                border: `1px solid ${isPaid ? '#bae7ff' : '#ffccc7'}`,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                padding: 0,
              }}
            >
              <span style={{ 
                color: isPaid ? '#0958d9' : '#ff4d4f', 
                fontWeight: 600, 
                fontSize: '12px',
              }}>
                {record.payment_status || 'Chưa thanh toán'}
              </span>
            </Button>
          </div>
        );
      },
    },
    {
      title: 'CCCD',
      dataIndex: 'citizen_id',
      key: 'citizen_id',
      width: 120,
      render: (text) => text || '•'
    },
    {
      title: 'THAO TÁC NHANH',
      key: 'actions',
      width: 160,
      align: 'center',
      render: (text, record) => (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px 6px', justifyContent: 'center', alignItems: 'center', width: 'fit-content', margin: '0 auto' }} onClick={(e) => e.stopPropagation()}>
          <Tooltip title="Xuất nhanh bộ hồ sơ Word">
            <Button 
              type="text" 
              icon={<FileWordOutlined style={{ color: '#0f6cbd', fontSize: '18px' }} />} 
              onClick={() => handleQuickExportWord(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Gửi mail yêu cầu định giá">
            <Button 
              type="text" 
              icon={<MailOutlined style={{ color: '#059669', fontSize: '18px' }} />} 
              onClick={() => handleOpenAppraisalMail(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Gửi mail phát hành chứng thư">
            <Button 
              type="text" 
              icon={<SendOutlined style={{ color: '#8b5cf6', fontSize: '18px' }} />} 
              onClick={() => handleOpenDelivery(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Gửi yêu cầu định giá lên web">
            <Button 
              type="text" 
              icon={<GlobalOutlined style={{ color: '#ea4335', fontSize: '18px' }} />} 
              onClick={() => handleSubmitCaseToWeb(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Xóa">
            <Button 
              type="text" 
              danger
              icon={<DeleteOutlined style={{ fontSize: '18px' }} />} 
              onClick={() => handleDelete(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#fef2f2', border: 'none', padding: 0 }}
            />
          </Tooltip>
        </div>
      ),
    },
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys)
  };

  return (
    <div>
      {/* Search & filters panel */}
      <CaseFilterBar 
        filterOptions={filterOptions} 
        filters={filters} 
        onFilterChange={setFilters} 
      />

      {/* Main Case Table Card */}
      <Card 
        style={{ borderRadius: 12, border: '1px solid #dbe3f3' }} 
        bodyStyle={{ padding: 0 }}
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
            <span style={{ fontSize: 16, fontWeight: 700 }}>Danh sách hồ sơ thẩm định</span>
            <Space wrap>
              <Button 
                type="primary" 
                icon={<PlusOutlined />} 
                onClick={() => { setEditingCase(null); setEditModalOpen(true); }}
                style={{ borderRadius: 6 }}
              >
                Thêm hồ sơ
              </Button>
              <Button 
                icon={<UploadOutlined />} 
                onClick={() => setImportModalOpen(true)}
                style={{ borderRadius: 6 }}
              >
                Import Excel
              </Button>
              <Button 
                icon={<DownloadOutlined />} 
                onClick={handleExport}
                style={{ borderRadius: 6 }}
              >
                Export Excel
              </Button>
            </Space>
          </div>
        }
      >
        <Table
          bordered
          {...getResizableProps(columns)}
          dataSource={data.items}
          rowKey="id"
          loading={loading}
          scroll={{ x: 'max-content' }}
          pagination={{
            current: filters.page,
            pageSize: filters.size,
            total: data.total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '15', '20', '50'],
            showTotal: (total) => `Tổng số: ${total} hồ sơ`
          }}
          onChange={handleTableChange}
          onRow={(record) => ({
            onDoubleClick: () => {
              navigate(`/cases/${record.id}`);
            },
            onClick: () => {
              setEditingCase(record);
              setEditModalOpen(true);
            },
            style: { cursor: 'pointer' }
          })}
        />
      </Card>

      {/* Edit/Create Modal */}
      <CaseEditModal
        open={editModalOpen}
        caseData={editingCase}
        filterOptions={filterOptions}
        onCancel={() => { setEditModalOpen(false); setEditingCase(null); }}
        onSave={handleSaveCase}
      />

      {/* Import Modal */}
      <CaseImportModal
        open={importModalOpen}
        onCancel={() => setImportModalOpen(false)}
        onSuccess={() => { setImportModalOpen(false); fetchCases(); if (onFilterOptionsRefresh) onFilterOptionsRefresh(); }}
      />

      <Modal
        open={appraisalMailOpen}
        title="Tùy chọn gửi mail cho Nghiệp vụ"
        okText="Gửi mail"
        cancelText="Hủy"
        confirmLoading={sendingAppraisalMail}
        onCancel={() => { setAppraisalMailOpen(false); setActiveCaseForAppraisalMail(null); }}
        onOk={handleSendAppraisalMail}
        destroyOnClose
      >
        <p>Gửi mail yêu cầu định giá theo hồ sơ đã chọn.</p>
        <Form form={appraisalMailForm} layout="vertical">
          <Form.Item name="professional_forward_enabled" valuePropName="checked">
            <Checkbox>Chuyển tiếp cho Nghiệp vụ khi Hành chính trả lời</Checkbox>
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(previous, current) => previous.professional_forward_enabled !== current.professional_forward_enabled}>
            {({ getFieldValue }) => getFieldValue('professional_forward_enabled') ? (
              <Form.Item
                name="professional_recipient_email"
                label="Người nhận Nghiệp vụ"
                rules={[{ required: true, message: 'Vui lòng chọn người nhận Nghiệp vụ.' }]}
              >
                <Select>
                  <Select.Option value="Kietna@cenvalue.vn">Kietna@cenvalue.vn</Select.Option>
                  <Select.Option value="anhvtn6@cenvalue.vn">anhvtn6@cenvalue.vn</Select.Option>
                  <Select.Option value="truongpnt@cenvalue.vn">truongpnt@cenvalue.vn</Select.Option>
                </Select>
              </Form.Item>
            ) : null}
          </Form.Item>
        </Form>
      </Modal>

      {/* Delivery/Phat Hanh Modal */}
      <DeliveryModal
        open={deliveryOpen}
        onClose={() => { setDeliveryOpen(false); setActiveCaseForDelivery(null); }}
        caseId={activeCaseForDelivery?.id}
        onSuccess={() => fetchCases()}
      />

      {/* Notes Drawer */}
      <Drawer
        title={activeCaseForNotes ? `Ghi chú hồ sơ: ${activeCaseForNotes.contract_number || 'N/A'}` : 'Ghi chú'}
        placement="right"
        width={400}
        onClose={() => { setNotesDrawerOpen(false); setActiveCaseForNotes(null); }}
        open={notesDrawerOpen}
      >
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ flexGrow: 1, overflowY: 'auto', marginBottom: 20 }}>
            <List
              dataSource={notesList}
              locale={{ emptyText: 'Chưa có ghi chú nào.' }}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    description={
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ color: '#0f172a', fontSize: 13, wordBreak: 'break-all' }}>{item.note}</span>
                        <span style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                          Cập nhật: {item.created_at || 'Không rõ'}
                        </span>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </div>

          <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 16 }}>
            <Input.TextArea
              rows={3}
              value={newNoteText}
              onChange={(e) => setNewNoteText(e.target.value)}
              placeholder="Nhập nội dung ghi chú..."
              style={{ marginBottom: 12, borderRadius: 6 }}
            />
            <Button
              type="primary"
              onClick={handleAddNoteSubmit}
              loading={addingNote}
              style={{ width: '100%', borderRadius: 6 }}
              disabled={!newNoteText.trim()}
            >
              Thêm ghi chú
            </Button>
          </div>
        </div>
      </Drawer>
    </div>
  );
}
