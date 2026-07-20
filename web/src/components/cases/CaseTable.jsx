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
  CalendarOutlined,
  FormOutlined,
  IdcardOutlined,
  FileAddOutlined,
  CopyOutlined,
  CheckSquareOutlined
} from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useResizableColumns } from '../../hooks/useResizableColumns';
import client from '../../api/client';
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
import { 
  generateDocuments, 
  downloadAllZip, 
  downloadPhathanhDocx,
  getPhathanhContent,
  getXinsoContent,
  getLatestEmail,
  getDeliveryContacts,
  saveDelivery
} from '../../api/documents';
import { sendEmail as sendAppraisalEmail, submitWeb } from '../../api/entry';
import CaseFilterBar from './CaseFilterBar';
import CaseEditModal from './CaseEditModal';
import CaseImportModal from './CaseImportModal';
import DeliveryModal from './DeliveryModal';
import TaskModal from '../tasks/TaskModal';
import './CaseTable.css';

const getCaseRowClassName = (record) => {
  const status = record.case_status || 'Đang xử lý';

  if (status === 'Hoàn thành') {
    return 'case-table-row case-table-row--completed';
  }

  if (status === 'Đang xử lý' || status === 'Đang thực hiện') {
    return 'case-table-row case-table-row--in-progress';
  }

  return 'case-table-row';
};

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
  const [webAssetModalOpen, setWebAssetModalOpen] = useState(false);
  const [activeCaseForWeb, setActiveCaseForWeb] = useState(null);
  const [webAssetOptions, setWebAssetOptions] = useState([]);
  const [selectedWebAssetKeys, setSelectedWebAssetKeys] = useState([]);
  const [submittingWeb, setSubmittingWeb] = useState(false);

  const [deliveryOpen, setDeliveryOpen] = useState(false);
  const [activeCaseForDelivery, setActiveCaseForDelivery] = useState(null);
  const [phathanhDeliveryOpen, setPhathanhDeliveryOpen] = useState(false);
  const [activeCaseForPhathanh, setActiveCaseForPhathanh] = useState(null);
  const [phathanhDeliveryContacts, setPhathanhDeliveryContacts] = useState([]);
  const [loadingPhathanhDeliveryContacts, setLoadingPhathanhDeliveryContacts] = useState(false);
  const [creatingPhathanhForm, setCreatingPhathanhForm] = useState(false);
  const [phathanhDeliverySearch, setPhathanhDeliverySearch] = useState('');
  const [phathanhDeliveryForm] = Form.useForm();
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [activeCaseForTask, setActiveCaseForTask] = useState(null);

  // States for copy-paste content popups
  const [contentModalOpen, setContentModalOpen] = useState(false);
  const [contentModalTitle, setContentModalTitle] = useState('');
  const [contentModalHtml, setContentModalHtml] = useState('');

  // States for latest email viewer popup
  const [latestEmailModalOpen, setLatestEmailModalOpen] = useState(false);
  const [latestEmailData, setLatestEmailData] = useState(null);
  const [loadingLatestEmail, setLoadingLatestEmail] = useState(false);

  const selectedPhathanhDeliveryContactId = Form.useWatch('delivery_contact_id', phathanhDeliveryForm);
  const defaultDeliveryContactDetails = 'CÔNG TY CỔ PHẦN THẨM ĐỊNH GIÁ THẾ KỶ - VP TẠI GIA LAI\nĐịa chỉ: 90/60/3 Trường Chinh, TP. Pleiku, Gia Lai\nĐiện thoại: 0905226968';
  const selectedPhathanhDeliveryDetails = selectedPhathanhDeliveryContactId === 0
    ? defaultDeliveryContactDetails
    : (phathanhDeliveryContacts.find((contact) => contact.id === selectedPhathanhDeliveryContactId)?.full_details || '');

  // Format received email time to "HH:MM DD/MM/YYYY" format
  const formatLatestEmailTime = (timeStr) => {
    if (!timeStr) return 'N/A';
    if (timeStr === 'Live Inbox') return 'Hộp thư trực tiếp (Đang quét)';
    try {
      const date = new Date(timeStr);
      if (isNaN(date.getTime())) return timeStr;
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const year = date.getFullYear();
      return `${hours}:${minutes} ${day}/${month}/${year}`;
    } catch (e) {
      return timeStr;
    }
  };

  // Copy HTML Rich Text helper
  const handleCopyHtml = async () => {
    if (!contentModalHtml) return;
    try {
      const blob = new Blob([contentModalHtml], { type: 'text/html' });
      // Plain text fallback
      const plainText = contentModalHtml.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
      const textBlob = new Blob([plainText], { type: 'text/plain' });
      
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': blob,
          'text/plain': textBlob
        })
      ]);
      message.success('Đã sao chép định dạng bảng (Rich Text) thành công! Bạn có thể dán trực tiếp vào Outlook/Gmail.');
    } catch (err) {
      console.error(err);
      try {
        const listener = (e) => {
          e.clipboardData.setData('text/html', contentModalHtml);
          e.preventDefault();
        };
        document.addEventListener('copy', listener);
        document.execCommand('copy');
        document.removeEventListener('copy', listener);
        message.success('Đã sao chép nội dung vào Clipboard!');
      } catch (fallbackErr) {
        message.error('Không thể sao chép tự động. Vui lòng bôi đen và copy thủ công.');
      }
    }
  };

  const fetchPhathanhDeliveryContacts = async () => {
    setLoadingPhathanhDeliveryContacts(true);
    try {
      const res = await getDeliveryContacts();
      setPhathanhDeliveryContacts(res.data || []);
    } catch (err) {
      console.error(err);
      message.error('Không thể tải danh bạ chuyển phát');
    } finally {
      setLoadingPhathanhDeliveryContacts(false);
    }
  };

  const handleOpenPhathanhDeliveryModal = (record) => {
    setActiveCaseForPhathanh(record);
    phathanhDeliveryForm.setFieldsValue({
      delivery_contact_id: record.delivery_contact_id || 0,
      delivery_quantity: '2',
    });
    setPhathanhDeliverySearch('');
    setPhathanhDeliveryOpen(true);
    fetchPhathanhDeliveryContacts();
  };

  const handleCreatePhathanhContentWithDelivery = async () => {
    if (!activeCaseForPhathanh) return;

    setCreatingPhathanhForm(true);
    try {
      const values = await phathanhDeliveryForm.validateFields();
      await saveDelivery(activeCaseForPhathanh.id, {
        delivery_contact_id: values.delivery_contact_id,
        manual_short_name: '',
        manual_details: '',
        save_to_contacts: false,
      });
      setPhathanhDeliveryOpen(false);
      setActiveCaseForPhathanh(null);
      await handleOpenPhathanhContent(activeCaseForPhathanh, values.delivery_quantity);
    } catch (err) {
      if (err?.errorFields) return;
      console.error(err);
      message.error(err.response?.data?.error || 'Không thể lưu thông tin chuyển phát để tạo form.');
    } finally {
      setCreatingPhathanhForm(false);
    }
  };

  // Open "Tạo form phát hành chứng thư" content
  const handleOpenPhathanhContent = async (record, deliveryQuantity) => {
    const hide = message.loading('Đang lấy nội dung phát hành...', 0);
    try {
      const res = await getPhathanhContent(record.id, deliveryQuantity);
      setContentModalTitle(`Nội dung phát hành chứng thư: ${record.contract_number || record.id}`);
      setContentModalHtml(res.data.html || '');
      setContentModalOpen(true);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Không thể lấy nội dung phát hành.');
    } finally {
      hide();
    }
  };

  // Open "Tạo form xin số chứng thư" content
  const handleOpenXinsoContent = async (record) => {
    const hide = message.loading('Đang lấy nội dung xin số...', 0);
    try {
      const res = await getXinsoContent(record.id);
      setContentModalTitle(`Nội dung xin số chứng thư: ${record.contract_number || record.id}`);
      setContentModalHtml(res.data.html || '');
      setContentModalOpen(true);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Không thể lấy nội dung xin số.');
    } finally {
      hide();
    }
  };

  // Open "Xem mail mới nhất" popup
  const handleOpenLatestEmail = async (record) => {
    setLoadingLatestEmail(true);
    setLatestEmailModalOpen(true);
    setLatestEmailData(null);
    try {
      const res = await getLatestEmail(record.id);
      setLatestEmailData(res.data.email || null);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Không thể tải email mới nhất.');
    } finally {
      setLoadingLatestEmail(false);
    }
  };

  // 1. Quick Word Export
  const handleQuickExportWord = async (record) => {
const hide = message.loading('Đang xuất nhanh bộ hồ sơ Word...', 0);
try {
const generateResponse = await generateDocuments(record.id);
// Download all documents ZIP
const response = await downloadAllZip(record.id);
const url = window.URL.createObjectURL(new Blob([response.data]));
const link = document.createElement('a');
link.href = url;
const rawFolderName = generateResponse.data?.folder_name || `hoso_word_${record.id}`;
const safeFolderName = String(rawFolderName).replace(/[<>:"/\\|?*]+/g, '-').replace(/\s+/g, ' ').trim();
link.setAttribute('download', `${safeFolderName || `hoso_word_${record.id}`}.zip`);
document.body.appendChild(link);
link.click();
link.parentNode.removeChild(link);
window.URL.revokeObjectURL(url);
message.success('Xuất hồ sơ Word thành công! Đang tải về...');
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

  const handleOpenTaskModal = (record) => {
    setActiveCaseForTask(record);
    setTaskModalOpen(true);
  };

  const handleCreateTask = async (payload) => {
    await client.post('/tasks', {
      ...payload,
      case_id: activeCaseForTask?.id ?? payload.case_id,
      status: 'todo',
    });
    message.success('Đã tạo công việc cho hồ sơ');
    setTaskModalOpen(false);
    setActiveCaseForTask(null);
  };

  // 4. Submit valuation request to Web automation
  const buildWebAssetOptions = (caseData) => {
    const description = String(caseData.asset_description || '').trim();
    const lines = description
      .split(/\r?\n+/)
      .map((line) => line.trim())
      .filter(Boolean);
    const sourceLines = lines.length > 0 ? lines : [description || caseData.contract_number || `Hồ sơ #${caseData.id}`];
    return sourceLines.map((line, index) => ({
      key: String(index),
      index: index + 1,
      asset_description: line,
      so_to_ban_do: caseData.so_to_ban_do || '',
      so_thua_dat: caseData.so_thua_dat || '',
    }));
  };

  const handleOpenSubmitWebModal = async (record) => {
    try {
      const res = await getCase(record.id);
      const caseData = res.data || record;
      const options = buildWebAssetOptions(caseData);
      if (options.length === 1) {
        const hide = message.loading('Đang gửi yêu cầu định giá lên Web...', 0);
        setSubmittingWeb(true);
        try {
          const payload = {
            ...caseData,
            asset_description: options[0].asset_description,
            customer_phone: caseData.customer_phone || '',
            citizen_id: caseData.citizen_id || '',
            personal_note: caseData.personal_note || '',
            advance_payment: caseData.advance_payment ? String(caseData.advance_payment) : '0',
          };
          const submitRes = await submitWeb(payload);
          message.success(submitRes.data?.message || 'Gửi yêu cầu lên Web thành công! 🌐');
        } finally {
          setSubmittingWeb(false);
          hide();
        }
        return;
      }
      setActiveCaseForWeb(caseData);
      setWebAssetOptions(options);
      setSelectedWebAssetKeys(options.map((item) => item.key));
      setWebAssetModalOpen(true);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Không tải được thông tin hồ sơ để gửi Web.');
    }
  };

  const handleSubmitCaseToWeb = async () => {
    if (!activeCaseForWeb) return;
    const selectedAssets = webAssetOptions.filter((item) => selectedWebAssetKeys.includes(item.key));
    if (selectedAssets.length === 0) {
      message.warning('Vui lòng chọn ít nhất một tài sản để gửi lên Web.');
      return;
    }
    const hide = message.loading('Đang gửi yêu cầu định giá lên Web...', 0);
    setSubmittingWeb(true);
    try {
      const caseData = activeCaseForWeb;
      const selectedDescription = selectedAssets.map((item) => item.asset_description).join('\n');
      
      const payload = {
        ...caseData,
        asset_description: selectedDescription,
        customer_phone: caseData.customer_phone || '',
        citizen_id: caseData.citizen_id || '',
        personal_note: caseData.personal_note || '',
        advance_payment: caseData.advance_payment ? String(caseData.advance_payment) : '0',
      };
      
      const submitRes = await submitWeb(payload);
      message.success(submitRes.data?.message || 'Gửi yêu cầu lên Web thành công! 🌐');
      setWebAssetModalOpen(false);
      setActiveCaseForWeb(null);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Gửi yêu cầu lên Web thất bại.');
    } finally {
      setSubmittingWeb(false);
      hide();
    }
  };

  // 5. Download certificate release form docx
  const handleDownloadPhathanhDocx = async (record) => {
    const hide = message.loading('Đang tạo form phát hành chứng thư...', 0);
    try {
      const response = await downloadPhathanhDocx(record.id);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const contractNum = record.contract_number ? record.contract_number.replace(/\//g, '_') : record.id;
      link.setAttribute('download', `phieu_phat_hanh_${contractNum}.docx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      message.success('Tải form phát hành chứng thư thành công! 📄');
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Tạo form phát hành chứng thư thất bại.');
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
          bg: '#e8f5f3',
          color: '#007f7a',
          border: '#9dd6d1',
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
    actions: 160
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
              <Link
                to={`/cases/${record.id}`}
                onClick={(event) => event.stopPropagation()}
                title="Xem chi tiết hồ sơ"
                style={{
                  fontSize: '11px',
                  color: '#4f46e5',
                  backgroundColor: '#e0e7ff',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontWeight: 700,
                  textDecoration: 'none',
                }}
              >
                #{record.id}
              </Link>
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
                <IdcardOutlined style={{ color: '#64748b', marginRight: '6px' }} />
                <span>
                  <span style={{ color: '#475569', fontWeight: 600 }}>CCCD: </span>
                  <span style={{ color: '#0f172a', fontWeight: 'normal' }}>{record.citizen_id || '-'}</span>
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
      render: (text) => {
        if (!text) return '-';
        const items = text.split('\n').map(item => item.trim()).filter(Boolean);
        if (items.length === 0) return '-';
        return (
          <ul style={{ margin: 0, paddingLeft: '16px', listStyleType: 'disc', whiteSpace: 'normal' }}>
            {items.map((item, idx) => (
              <li key={idx} style={{ marginBottom: idx === items.length - 1 ? 0 : '4px' }}>
                {item}
              </li>
            ))}
          </ul>
        );
      }
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
      title: 'THAO TÁC NHANH',
      key: 'actions',
      width: 200,
      align: 'center',
        render: (text, record) => (
          <div className="case-table-actions" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 36px)', gap: '8px 8px', justifyContent: 'center', alignItems: 'center', width: 'fit-content', margin: '0 auto' }} onClick={(e) => e.stopPropagation()}>
          <Tooltip title="Gửi mail yêu cầu định giá">
            <Button 
              type="text" 
              icon={<MailOutlined style={{ color: '#059669', fontSize: '18px' }} />} 
              onClick={() => handleOpenAppraisalMail(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Tạo form xin số chứng thư">
            <Button 
              type="text" 
              icon={<FileAddOutlined style={{ color: '#0284c7', fontSize: '18px' }} />} 
              onClick={() => handleOpenXinsoContent(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Xem mail mới nhất">
            <Button 
              type="text" 
              icon={<CommentOutlined style={{ color: '#0891b2', fontSize: '18px' }} />} 
              onClick={() => handleOpenLatestEmail(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Gửi yêu cầu định giá lên web">
            <Button 
              type="text" 
              icon={<GlobalOutlined style={{ color: '#ea4335', fontSize: '18px' }} />} 
              onClick={() => handleOpenSubmitWebModal(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Xuất nhanh bộ hồ sơ Word">
            <Button 
              type="text" 
              icon={<FileWordOutlined style={{ color: '#007f7a', fontSize: '18px' }} />} 
              onClick={() => handleQuickExportWord(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Tạo công việc">
            <Button
              type="text"
              icon={<CheckSquareOutlined style={{ color: '#7c3aed', fontSize: '18px' }} />}
              onClick={() => handleOpenTaskModal(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f5f3ff', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Gửi mail phát hành chứng thư">
            <Button 
              type="text" 
              icon={<SendOutlined style={{ color: '#d99a55', fontSize: '18px' }} />} 
              onClick={() => handleOpenDelivery(record)}
              style={{ width: '36px', height: '36px', minWidth: '36px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '6px', backgroundColor: '#f1f5f9', border: 'none', padding: 0 }}
            />
          </Tooltip>
          <Tooltip title="Tạo form phát hành chứng thư">
            <Button 
              type="text" 
              icon={<FormOutlined style={{ color: '#d97706', fontSize: '18px' }} />} 
              onClick={() => handleOpenPhathanhDeliveryModal(record)}
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
        style={{ borderRadius: 12, border: '1px solid #d8e7e5' }} 
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
          rowClassName={getCaseRowClassName}
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
        open={webAssetModalOpen}
        title="Chọn tài sản gửi yêu cầu định giá lên Web"
        okText="Gửi lên Web"
        cancelText="Hủy"
        confirmLoading={submittingWeb}
        onCancel={() => {
          setWebAssetModalOpen(false);
          setActiveCaseForWeb(null);
        }}
        onOk={handleSubmitCaseToWeb}
        width={900}
        destroyOnClose
      >
        <Table
          size="small"
          rowKey="key"
          dataSource={webAssetOptions}
          pagination={false}
          rowSelection={{
            selectedRowKeys: selectedWebAssetKeys,
            onChange: setSelectedWebAssetKeys,
          }}
          columns={[
            { title: 'STT', dataIndex: 'index', width: 70 },
            { title: 'Tài sản', dataIndex: 'asset_description' },
            { title: 'Số tờ', dataIndex: 'so_to_ban_do', width: 120 },
            { title: 'Số thửa', dataIndex: 'so_thua_dat', width: 120 },
          ]}
        />
      </Modal>

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

      <Modal
        open={phathanhDeliveryOpen}
        title="Chọn thông tin chuyển phát để tạo form"
        okText="Tạo form phát hành"
        cancelText="Hủy"
        confirmLoading={creatingPhathanhForm}
        onCancel={() => {
          setPhathanhDeliveryOpen(false);
          setActiveCaseForPhathanh(null);
          setPhathanhDeliverySearch('');
          phathanhDeliveryForm.resetFields();
        }}
        onOk={handleCreatePhathanhContentWithDelivery}
        destroyOnClose
        width={600}
      >
        <Form form={phathanhDeliveryForm} layout="vertical">
          <Form.Item label="Số chứng thư phát hành">
            <Input value={activeCaseForPhathanh?.contract_number || ''} disabled />
          </Form.Item>

          <Form.Item
            name="delivery_contact_id"
            label="Chọn người nhận chuyển phát"
            rules={[{ required: true, message: 'Vui lòng chọn người nhận chuyển phát' }]}
          >
            <Select
              placeholder="Chọn từ danh bạ..."
              loading={loadingPhathanhDeliveryContacts}
              showSearch
              searchValue={phathanhDeliverySearch}
              onSearch={setPhathanhDeliverySearch}
              onDropdownOpenChange={(visible) => {
                if (visible) setPhathanhDeliverySearch('');
              }}
              optionFilterProp="label"
              filterOption={(input, option) =>
                String(option?.label || '').toLowerCase().includes(input.toLowerCase())
              }
              options={[
                { value: 0, label: 'VP Gia Lai (mặc định) - 90/60/3 Trường Chinh' },
                ...phathanhDeliveryContacts.map((contact) => ({
                  value: contact.id,
                  label: `${contact.short_name} (${contact.full_details.split('\n')[0] || ''})`,
                })),
              ]}
            />
          </Form.Item>

          <Form.Item
            name="delivery_quantity"
            label="Số lượng hồ sơ gửi"
            rules={[
              { required: true, message: 'Vui lòng nhập số lượng hồ sơ gửi' },
              { pattern: /^[1-9]\d*$/, message: 'Số lượng hồ sơ gửi phải là số nguyên dương' },
            ]}
          >
            <Input placeholder="Ví dụ: 2" />
          </Form.Item>

          <Form.Item label="Thông tin chuyển phát">
            <Input.TextArea
              value={selectedPhathanhDeliveryDetails}
              rows={4}
              readOnly
              placeholder="Chọn người nhận chuyển phát để kiểm tra thông tin"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Delivery/Phat Hanh Modal */}
      <DeliveryModal
        open={deliveryOpen}
        onClose={() => { setDeliveryOpen(false); setActiveCaseForDelivery(null); }}
        caseId={activeCaseForDelivery?.id}
        contractNumber={activeCaseForDelivery?.contract_number}
        onSuccess={() => fetchCases()}
      />

      <TaskModal
        open={taskModalOpen}
        defaultCaseId={activeCaseForTask?.id}
        onCancel={() => { setTaskModalOpen(false); setActiveCaseForTask(null); }}
        onSubmit={handleCreateTask}
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

      {/* Content Display Modal (Copy-paste form) */}
      <Modal
        title={<span style={{ fontSize: 16, fontWeight: 700 }}>{contentModalTitle}</span>}
        open={contentModalOpen}
        onCancel={() => setContentModalOpen(false)}
        width={1100}
        footer={[
          <Button key="close" onClick={() => setContentModalOpen(false)}>
            Đóng
          </Button>,
          <Button 
            key="copy" 
            type="primary" 
            icon={<CopyOutlined />} 
            onClick={handleCopyHtml}
            style={{ backgroundColor: '#047857', borderColor: '#047857' }}
          >
            Sao chép bảng nội dung
          </Button>
        ]}
      >
        <div style={{ padding: '12px 0' }}>
          <p style={{ color: '#64748b', fontSize: 13, marginBottom: 12 }}>
            💡 Nội dung bảng dưới đây có thể được sao chép trực tiếp. Sau khi nhấn <strong>Sao chép bảng nội dung</strong>, bạn có thể dán (Ctrl+V) trực tiếp vào Outlook/Gmail để giữ nguyên định dạng bảng và màu sắc.
          </p>
          <div 
            style={{ 
              maxHeight: '550px', 
              overflowY: 'auto', 
              border: '1px solid #e2e8f0', 
              padding: '16px', 
              borderRadius: '8px', 
              backgroundColor: '#ffffff',
              boxShadow: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.05)'
            }}
            dangerouslySetInnerHTML={{ __html: contentModalHtml }}
          />
        </div>
      </Modal>

      {/* Latest Email Viewer Modal */}
      <Modal
        title={<span style={{ fontSize: 16, fontWeight: 700 }}>Email mới nhất từ Mail-Listener</span>}
        open={latestEmailModalOpen}
        onCancel={() => setLatestEmailModalOpen(false)}
        width={1200}
        footer={[
          <Button key="close" onClick={() => setLatestEmailModalOpen(false)}>
            Đóng
          </Button>
        ]}
      >
        {loadingLatestEmail ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Badge status="processing" text="Đang tải email mới nhất..." />
          </div>
        ) : latestEmailData ? (
          <div style={{ padding: '12px 0' }}>
            <div style={{ backgroundColor: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: 16 }}>
              <div style={{ marginBottom: 8 }}><strong style={{ color: '#475569' }}>Tiêu đề:</strong> <span style={{ fontWeight: 600, color: '#0f172a' }}>{latestEmailData.subject}</span></div>
              <div style={{ marginBottom: 8 }}><strong style={{ color: '#475569' }}>Người gửi:</strong> <span style={{ color: '#0f172a' }}>{latestEmailData.from_email}</span></div>
              <div><strong style={{ color: '#475569' }}>Thời gian:</strong> <span style={{ color: '#64748b' }}>{formatLatestEmailTime(latestEmailData.processed_at)}</span></div>
            </div>
            
            <strong style={{ color: '#475569', display: 'block', marginBottom: 8 }}>Nội dung email:</strong>
            <div 
              style={{ 
                maxHeight: '600px', 
                overflowY: 'auto', 
                border: '1px solid #e2e8f0', 
                padding: '16px', 
                borderRadius: '8px', 
                backgroundColor: '#ffffff',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                fontFamily: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif'
              }}
              dangerouslySetInnerHTML={{ __html: latestEmailData.body }}
            />
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '45px 0', color: '#64748b' }}>
            📭 Chưa nhận được email tương ứng nào từ mail-listener cho hồ sơ này trong cơ sở dữ liệu.
          </div>
        )}
      </Modal>
    </div>
  );
}
