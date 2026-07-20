import React, { useState, useEffect, useCallback } from 'react';
import { Card, Typography, Row, Col, Input, Select, Button, Space, message, Spin } from 'antd';
import {
  SyncOutlined,
  MailOutlined,
  SearchOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { useAuth } from '../hooks/useAuth';
import {
  getSoboRecords,
  getSoboStats,
  deleteSoboRecord,
  unfollowSoboRecord,
  syncTelegram,
  checkMail
} from '../api/sobo';
import { createCase } from '../api/cases';
import SoboTable from '../components/sobo/SoboTable';
import SoboDetailDrawer from '../components/sobo/SoboDetailDrawer';
import SoboEditModal from '../components/sobo/SoboEditModal';
import CaseEditModal from '../components/cases/CaseEditModal';

const { Title, Text, Paragraph } = Typography;

export default function Sobo() {
  const { isGuest } = useAuth();
  
  // Data State
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  
  // KPI Stats State
  const [stats, setStats] = useState({
    pending_count: 0,
    responded_count: 0,
    avg_duration_secs: 0,
    has_overdue: false
  });
  const [loadingStats, setLoadingStats] = useState(false);

  // Filters State
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    showSizeChanger: true,
    pageSizeOptions: ['10', '20', '50']
  });
  const [sorter, setSorter] = useState({
    field: 'id',
    order: 'desc'
  });

  // Modals & Drawer State
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState(null);
  
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [recordToEdit, setRecordToEdit] = useState(null);
  const [convertModalOpen, setConvertModalOpen] = useState(false);
  const [caseDraft, setCaseDraft] = useState(null);

  // Loading Action States
  const [syncingTelegram, setSyncingTelegram] = useState(false);
  const [checkingMail, setCheckingMail] = useState(false);

  // Fetch KPI Stats
  const fetchStats = useCallback(async () => {
    setLoadingStats(true);
    try {
      const res = await getSoboStats();
      setStats(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingStats(false);
    }
  }, []);

  // Fetch paginated records list
  const fetchRecords = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        search: search.trim(),
        status: statusFilter,
        page: pagination.current,
        size: pagination.pageSize,
        sort: sorter.field,
        order: sorter.order
      };
      const res = await getSoboRecords(params);
      setRecords(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error(err);
      message.error('Lỗi khi tải danh sách hồ sơ sơ bộ');
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, pagination.current, pagination.pageSize, sorter.field, sorter.order]);

  // Load initial data
  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  // Handle table pagination, sorting & filtering
  const handleTableChange = (pag, filters, sort) => {
    setPagination((prev) => ({
      ...prev,
      current: pag.current,
      pageSize: pag.pageSize
    }));

    if (sort && sort.field) {
      setSorter({
        field: sort.field,
        order: sort.order === 'ascend' ? 'asc' : 'desc'
      });
    }
  };

  // Run Telegram sync
  const handleSyncTelegram = async () => {
    setSyncingTelegram(true);
    const hideLoading = message.loading('Đang đồng bộ hồ sơ từ Telegram & Hộp thư...', 0);
    try {
      const res = await syncTelegram();
      const count = res.data.total || 0;
      if (count > 0) {
        message.success(`Đồng bộ thành công! Đã thêm/cập nhật ${count} hồ sơ sơ bộ mới.`);
      } else {
        message.info('Không phát hiện hồ sơ sơ bộ mới trên Telegram hoặc Hộp thư.');
      }
      fetchStats();
      fetchRecords();
    } catch (err) {
      console.error(err);
      message.error('Lỗi khi đồng bộ Telegram: ' + (err.response?.data?.error || err.message));
    } finally {
      hideLoading();
      setSyncingTelegram(false);
    }
  };

  // Run Mail check
  const handleCheckMail = async () => {
    setCheckingMail(true);
    const hideLoading = message.loading('Đang kiểm tra và đồng bộ email phản hồi mới...', 0);
    try {
      const res = await checkMail();
      const count = res.data.processed_count || 0;
      if (count > 0) {
        message.success(`Đồng bộ thành công! Tìm thấy và xử lý ${count} email mới.`);
      } else {
        message.info('Không phát hiện phản hồi mail mới cho hồ sơ sơ bộ.');
      }
      fetchStats();
      fetchRecords();
    } catch (err) {
      console.error(err);
      message.error('Lỗi khi kiểm tra mail: ' + (err.response?.data?.error || err.message));
    } finally {
      hideLoading();
      setCheckingMail(false);
    }
  };

  // Delete handler
  const handleDelete = async (id) => {
    try {
      await deleteSoboRecord(id);
      message.success('Đã xóa hồ sơ thành công');
      fetchStats();
      fetchRecords();
    } catch (err) {
      console.error(err);
      message.error('Không thể xóa hồ sơ sơ bộ');
    }
  };

  const handleUnfollow = async (id) => {
    try {
      await unfollowSoboRecord(id);
      message.success('Đã bỏ theo dõi mail phản hồi cho hồ sơ');
      fetchStats();
      fetchRecords();
    } catch (err) {
      console.error(err);
      message.error('Không thể bỏ theo dõi hồ sơ sơ bộ');
    }
  };

  // Drawer handlers
  const handleOpenDetail = (record) => {
    setSelectedRecord(record);
    setDetailDrawerOpen(true);
  };

  // Edit Modal handlers
  const handleOpenEdit = (record) => {
    setRecordToEdit(record);
    setEditModalOpen(true);
  };

  const handleEditSuccess = () => {
    setEditModalOpen(false);
    setRecordToEdit(null);
    fetchStats();
    fetchRecords();
  };

  const buildCaseDraftFromSobo = (record) => {
    const assetDescription = record.asset_type === 'machinery'
      ? (record.equipment_name || record.note || '')
      : [
          record.so_thua ? `Thửa đất số ${record.so_thua}` : '',
          record.so_to ? `tờ bản đồ số ${record.so_to}` : '',
          record.dia_chi ? `tại ${record.dia_chi}` : '',
        ].filter(Boolean).join(', ');

    return {
      customer_type: 'individual',
      customer_info: record.owner_name || record.chu_so_huu || '',
      customer_address: record.owner_address || '',
      citizen_id: record.owner_citizen_id || '',
      source: record.source || '',
      asset_type: record.asset_type === 'machinery' ? 'Máy móc thiết bị' : (record.asset_sub_type || 'BĐS đặc thù khác'),
      asset_description: assetDescription,
      so_thua_dat: record.so_thua || '',
      so_to_ban_do: record.so_to || '',
      dia_chi_thua_dat: record.dia_chi || '',
      personal_note: [
        record.so_giay_chung_nhan ? `Số giấy chứng nhận: ${record.so_giay_chung_nhan}` : '',
        record.so_vao_so_cap_giay_chung_nhan ? `Số vào sổ cấp giấy chứng nhận: ${record.so_vao_so_cap_giay_chung_nhan}` : '',
        record.ngay_cap_giay_chung_nhan ? `Ngày cấp giấy chứng nhận: ${record.ngay_cap_giay_chung_nhan}` : '',
        record.note ? `Ghi chú sơ bộ: ${record.note}` : '',
        record.response_content ? `Phản hồi sơ bộ: ${record.response_content}` : '',
      ].filter(Boolean).join('\n'),
      original_file_path: record.attachment_paths || '',
      case_status: 'Đang xử lý',
      payment_status: 'Chưa thanh toán',
      execution_month: `${String(new Date().getMonth() + 1).padStart(2, '0')}/${new Date().getFullYear()}`,
    };
  };

  const handleConvertToCase = (record) => {
    setCaseDraft(buildCaseDraftFromSobo(record));
    setConvertModalOpen(true);
  };

  const handleSaveConvertedCase = async (values) => {
    try {
      await createCase(values);
      message.success('Đã chuyển hồ sơ sơ bộ sang thẩm định.');
      setConvertModalOpen(false);
      setCaseDraft(null);
    } catch (err) {
      console.error(err);
      message.error(err.response?.data?.error || 'Chuyển sang thẩm định thất bại.');
    }
  };

  // Duration Formatter Helper
  const formatDuration = (seconds) => {
    if (!seconds || seconds <= 0) return '-';
    const totalHours = Math.floor(seconds / 3600);
    const days = Math.floor(totalHours / 24);
    const hours = totalHours % 24;
    if (days > 0) return `${days} ngày ${hours}g`;
    return `${hours}g`;
  };

  // Pulse style for overdue warning card
  const overdueCardStyle = (stats.has_overdue && stats.pending_count > 0)
    ? {
        borderLeft: '5px solid #c2413d',
        borderRight: '1px solid #fca5a5',
        borderTop: '1px solid #fca5a5',
        borderBottom: '1px solid #fca5a5',
        animation: 'pulse 1.5s infinite',
        boxShadow: '0 0 8px rgba(239, 68, 68, 0.2)'
      }
    : { borderLeft: '5px solid #c2413d' };

  return (
    <div style={{ padding: '0 8px' }}>
      {/* Dynamic Keyframes for pulsing red border */}
      <style>{`
        @keyframes pulse {
          0% { border-color: #fca5a5; box-shadow: 0 0 4px rgba(239, 68, 68, 0.15); }
          50% { border-color: #c2413d; box-shadow: 0 0 12px rgba(239, 68, 68, 0.45); }
          100% { border-color: #fca5a5; box-shadow: 0 0 4px rgba(239, 68, 68, 0.15); }
        }
      `}</style>

      {/* Title & Caption */}
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0, fontWeight: 700, color: '#0f172a' }}>
          📋 Giám sát yêu cầu Sơ bộ
        </Title>
        <Paragraph style={{ color: '#64748b', margin: '4px 0 0 0' }}>
          Theo dõi và cập nhật trạng thái phản hồi yêu cầu sơ bộ từ email phòng ban nghiệp vụ gửi qua Telegram bot.
          {isGuest && <Text type="warning" style={{ marginLeft: 8, fontWeight: 600 }}>[Tài khoản Khách - Chế độ Chỉ xem]</Text>}
        </Paragraph>
      </div>

      {/* KPI Stats Cards Grid */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8} style={{ display: 'flex' }}>
          <Card 
            bordered 
            style={{ 
              ...overdueCardStyle, 
              width: '100%', 
              display: 'flex', 
              flexDirection: 'column' 
            }}
            bodyStyle={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              padding: '16px 20px'
            }}
            hoverable
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  🔴 Chờ phản hồi
                </div>
                <div style={{ fontSize: '28px', fontWeight: 800, marginTop: 4, color: '#c2413d' }}>
                  {loadingStats ? <Spin size="small" /> : stats.pending_count}
                </div>
              </div>
              <div style={{ fontSize: '32px', color: '#fca5a5' }}>
                <ClockCircleOutlined />
              </div>
            </div>
            {stats.has_overdue && stats.pending_count > 0 && (
              <div style={{ marginTop: 8, fontSize: '12px', color: '#c2413d', fontWeight: 600 }}>
                ⚠️ Phát hiện hồ sơ trễ hạn phản hồi (&gt; 24h)
              </div>
            )}
          </Card>
        </Col>
        
        <Col xs={24} sm={8} style={{ display: 'flex' }}>
          <Card 
            bordered 
            style={{ 
              borderLeft: '5px solid #047857', 
              width: '100%', 
              display: 'flex', 
              flexDirection: 'column' 
            }}
            bodyStyle={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              padding: '16px 20px'
            }}
            hoverable
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  🟢 Đã phản hồi
                </div>
                <div style={{ fontSize: '28px', fontWeight: 800, marginTop: 4, color: '#047857' }}>
                  {loadingStats ? <Spin size="small" /> : stats.responded_count}
                </div>
              </div>
              <div style={{ fontSize: '32px', color: '#a7f3d0' }}>
                <CheckCircleOutlined />
              </div>
            </div>
            {stats.has_overdue && stats.pending_count > 0 && <div style={{ height: 18 }} />}
          </Card>
        </Col>

        <Col xs={24} sm={8} style={{ display: 'flex' }}>
          <Card 
            bordered 
            style={{ 
              borderLeft: '5px solid #007f7a', 
              width: '100%', 
              display: 'flex', 
              flexDirection: 'column' 
            }}
            bodyStyle={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              padding: '16px 20px'
            }}
            hoverable
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  ⚡ Thời gian phản hồi TB
                </div>
                <div style={{ fontSize: '28px', fontWeight: 800, marginTop: 4, color: '#007f7a' }}>
                  {loadingStats ? <Spin size="small" /> : formatDuration(stats.avg_duration_secs)}
                </div>
              </div>
              <div style={{ fontSize: '32px', color: '#bfdbfe' }}>
                <SyncOutlined />
              </div>
            </div>
            {stats.has_overdue && stats.pending_count > 0 && <div style={{ height: 18 }} />}
          </Card>
        </Col>
      </Row>

      {/* Control Filter Bar */}
      <Card style={{ marginBottom: 16, borderRadius: '8px' }} bodyStyle={{ padding: '16px 20px' }}>
        <Row gutter={[16, 16]} justify="space-between" align="middle">
          {/* Inputs filters */}
          <Col xs={24} md={12} lg={14}>
            <Space style={{ width: '100%' }} wrap>
              <Input
                placeholder="Tìm theo địa chỉ, thửa, tờ, nguồn..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPagination((prev) => ({ ...prev, current: 1 }));
                }}
                prefix={<SearchOutlined style={{ color: '#94a3b8' }} />}
                style={{ width: 280 }}
                allowClear
              />
              <Select
                placeholder="Lọc theo trạng thái"
                value={statusFilter}
                onChange={(val) => {
                  setStatusFilter(val);
                  setPagination((prev) => ({ ...prev, current: 1 }));
                }}
                style={{ width: 180 }}
                allowClear
              >
                <Select.Option value="">Tất cả trạng thái</Select.Option>
                <Select.Option value="PENDING">🔴 Chờ phản hồi</Select.Option>
                <Select.Option value="RESPONDED">🟢 Đã phản hồi</Select.Option>
              </Select>
            </Space>
          </Col>

          {/* Sync Buttons */}
          <Col xs={24} md={12} lg={10} style={{ textAlign: 'right' }}>
            <Space wrap>
              <Button
                type="primary"
                ghost
                icon={<SyncOutlined spin={syncingTelegram} />}
                onClick={handleSyncTelegram}
                disabled={isGuest}
                loading={syncingTelegram}
              >
                Đồng bộ Telegram
              </Button>
              <Button
                type="primary"
                icon={<MailOutlined />}
                onClick={handleCheckMail}
                disabled={isGuest}
                loading={checkingMail}
              >
                Kiểm tra Mail ngay
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Sobo Records Table */}
      <SoboTable
        loading={loading}
        dataSource={records}
        pagination={{
          ...pagination,
          total
        }}
        onChange={handleTableChange}
        onView={handleOpenDetail}
        onEdit={handleOpenEdit}
        onConvert={handleConvertToCase}
        onUnfollow={handleUnfollow}
        onDelete={handleDelete}
        isGuest={isGuest}
      />

      {/* Edit Modal (Admin only) */}
      <SoboEditModal
        open={editModalOpen}
        record={recordToEdit}
        onOk={handleEditSuccess}
        onCancel={() => {
          setEditModalOpen(false);
          setRecordToEdit(null);
        }}
      />

      <CaseEditModal
        open={convertModalOpen}
        caseData={caseDraft}
        onCancel={() => {
          setConvertModalOpen(false);
          setCaseDraft(null);
        }}
        onSave={handleSaveConvertedCase}
      />

      {/* Detail Drawer */}
      <SoboDetailDrawer
        open={detailDrawerOpen}
        record={selectedRecord}
        onClose={() => {
          setDetailDrawerOpen(false);
          setSelectedRecord(null);
        }}
      />
    </div>
  );
}
