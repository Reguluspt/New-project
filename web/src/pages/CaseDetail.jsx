import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  Card, Tabs, Button, Tag, Descriptions, Input, List, 
  Form, message, Skeleton, Space, Breadcrumb, Divider, Empty
} from 'antd';
import { 
  ArrowLeftOutlined, 
  EditOutlined, 
  InfoCircleOutlined, 
  FileTextOutlined, 
  CommentOutlined,
  SendOutlined,
  CheckSquareOutlined,
  PlusOutlined
} from '@ant-design/icons';
import { getCase, getNotes, addNote } from '../api/cases';
import client from '../api/client';
import CaseDocuments from '../components/cases/CaseDocuments';
import CaseEditModal from '../components/cases/CaseEditModal';
import TaskModal from '../components/tasks/TaskModal';

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editModalOpen, setEditModalOpen] = useState(false);
  
  // Notes tab states
  const [notes, setNotes] = useState([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [newNoteText, setNewNoteText] = useState('');
  const [submittingNote, setSubmittingNote] = useState(false);
  const [relatedTasks, setRelatedTasks] = useState([]);
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [taskModalOpen, setTaskModalOpen] = useState(false);

  useEffect(() => {
    if (id) {
      fetchCaseData();
      fetchNotes();
      fetchRelatedTasks();
    }
  }, [id]);

  const fetchCaseData = async () => {
    setLoading(true);
    try {
      const res = await getCase(id);
      setCaseData(res.data || null);
    } catch (err) {
      console.error(err);
      message.error('Không thể lấy thông tin hồ sơ');
    } finally {
      setLoading(false);
    }
  };

  const fetchNotes = async () => {
    setLoadingNotes(true);
    try {
      const res = await getNotes(id);
      setNotes(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingNotes(false);
    }
  };

  const fetchRelatedTasks = async () => {
    setLoadingTasks(true);
    try {
      const res = await client.get('/tasks', { params: { case_id: id } });
      setRelatedTasks(res.data?.items || []);
    } catch (err) {
      console.error(err);
      message.error('Không thể lấy danh sách công việc liên quan');
    } finally {
      setLoadingTasks(false);
    }
  };

  const handleCreateRelatedTask = async (payload) => {
    await client.post('/tasks', {
      ...payload,
      case_id: Number(id),
      status: 'todo',
    });
    message.success('Đã tạo công việc liên quan');
    setTaskModalOpen(false);
    fetchRelatedTasks();
  };

  const handleAddNote = async () => {
    const text = newNoteText.trim();
    if (!text) return;
    
    setSubmittingNote(true);
    try {
      await addNote(id, text);
      message.success('Đã thêm ghi chú');
      setNewNoteText('');
      fetchNotes();
    } catch (err) {
      console.error(err);
      message.error('Không thể thêm ghi chú');
    } finally {
      setSubmittingNote(false);
    }
  };

  const getStatusTag = (status) => {
    switch (status) {
      case 'Đã ký':
      case 'Hoàn thành':
        return <Tag color="green">{status}</Tag>;
      case 'Hủy':
        return <Tag color="red">{status}</Tag>;
      case 'Tạm dừng':
        return <Tag color="orange">{status}</Tag>;
      default:
        return <Tag color="blue">{status || 'Đang xử lý'}</Tag>;
    }
  };

  const getTaskStatusTag = (status) => {
    const labels = {
      todo: 'Cần làm',
      in_progress: 'Đang làm',
      review: 'Đánh giá',
      done: 'Hoàn thành',
    };
    const colors = {
      todo: 'default',
      in_progress: 'processing',
      review: 'warning',
      done: 'success',
    };
    return <Tag color={colors[status] || 'default'}>{labels[status] || status || 'Chưa đặt'}</Tag>;
  };

  const getTaskPriorityTag = (priority) => {
    const labels = {
      low: 'Thấp',
      medium: 'Trung bình',
      high: 'Cao',
    };
    const colors = {
      low: 'green',
      medium: 'gold',
      high: 'red',
    };
    return <Tag color={colors[priority] || 'default'}>{labels[priority] || priority || 'Chưa đặt'}</Tag>;
  };

  const formatTaskDueDate = (value) => {
    if (!value) return 'Chưa có hạn';
    const date = new Date(String(value).replace(' ', 'T'));
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5' }}>
          <Skeleton.Input active style={{ width: 300, marginBottom: 8 }} />
          <Skeleton active paragraph={{ rows: 1 }} title={false} />
        </Card>
        <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5' }}>
          <Skeleton active paragraph={{ rows: 8 }} />
        </Card>
      </div>
    );
  }

  if (!caseData) {
    return (
      <Card style={{ borderRadius: 12, textAlign: 'center', padding: '40px 0' }}>
        <h2>Không tìm thấy hồ sơ</h2>
        <p>Hồ sơ này có thể đã bị xóa hoặc không tồn tại.</p>
        <Button type="primary" onClick={() => navigate('/cases')}>
          Quay lại danh sách
        </Button>
      </Card>
    );
  }

  const tabItems = [
    {
      key: 'info',
      label: (
        <span>
          <InfoCircleOutlined />
          Thông tin chi tiết
        </span>
      ),
      children: (
        <Card style={{ borderRadius: 10, border: '1px solid #e5e7eb' }}>
          <Descriptions title="Hồ sơ chi tiết" bordered column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }}>
            <Descriptions.Item label="Số hợp đồng" span={1}>
              <strong style={{ color: '#007f7a' }}>{caseData.contract_number || 'N/A'}</strong>
            </Descriptions.Item>
            <Descriptions.Item label="Khách hàng" span={2}>
              {caseData.customer_info || 'N/A'} {caseData.customer_type === 'individual' ? '(Cá nhân)' : '(Tổ chức)'}
            </Descriptions.Item>
            
            <Descriptions.Item label="Địa chỉ khách hàng" span={3}>
              {caseData.customer_address || 'N/A'}
            </Descriptions.Item>

            <Descriptions.Item label="Địa chỉ tài sản" span={3}>
              {caseData.dia_chi_thua_dat || 'N/A'}
            </Descriptions.Item>

            <Descriptions.Item label="Mô tả tài sản" span={3}>
              {caseData.asset_description || 'N/A'}
            </Descriptions.Item>

            <Descriptions.Item label="Số thửa" span={1}>
              {caseData.so_thua_dat || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Số tờ" span={1}>
              {caseData.so_to_ban_do || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Chủ sở hữu" span={1}>
              {caseData.owner_name || 'N/A'}
            </Descriptions.Item>

            {caseData.gcn_details?.length > 0 && (
              <Descriptions.Item label="Thông tin từng GCN" span={3}>
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  {caseData.gcn_details.map((detail, index) => (
                    <Card key={detail.id || index} size="small" style={{ borderRadius: 6 }}>
                      <strong>GCN {index + 1}{detail.source_file_name ? ` - ${detail.source_file_name}` : ''}</strong>
                      <div>Số GCN: {detail.so_giay_chung_nhan || 'N/A'} | Số vào sổ: {detail.so_vao_so_cap_giay_chung_nhan || 'N/A'} | Ngày cấp: {detail.ngay_cap_giay_chung_nhan || 'N/A'}</div>
                      <div>Thửa: {detail.so_thua_dat || 'N/A'} | Tờ bản đồ: {detail.so_to_ban_do || 'N/A'}</div>
                      <div>Chủ sử dụng: {detail.owner_name || 'N/A'} | CCCD: {detail.owner_citizen_id || 'N/A'}</div>
                      <div>Địa chỉ thửa đất: {detail.dia_chi_thua_dat || 'N/A'}</div>
                      <div>Địa chỉ chủ sở hữu: {detail.owner_address || 'N/A'}</div>
                    </Card>
                  ))}
                </Space>
              </Descriptions.Item>
            )}

            <Descriptions.Item label="Tháng thực hiện" span={1}>
              {caseData.execution_month || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Mục đích định giá" span={2}>
              {caseData.valuation_purpose || 'N/A'}
            </Descriptions.Item>

            <Descriptions.Item label="Phí thẩm định" span={1}>
              {caseData.valuation_fee_number 
                ? `${caseData.valuation_fee_number.toLocaleString('vi-VN')} ?` 
                : '0 ?'
              }
            </Descriptions.Item>
            <Descriptions.Item label="Tạm ứng" span={1}>
              {caseData.advance_payment ? `${parseInt(caseData.advance_payment).toLocaleString('vi-VN')} ?` : '0 ?'}
            </Descriptions.Item>
            <Descriptions.Item label="Chi phí khảo sát" span={1}>
              {caseData.survey_cost ? `${parseInt(caseData.survey_cost).toLocaleString('vi-VN')} ?` : '0 ?'}
            </Descriptions.Item>

            <Descriptions.Item label="Thanh toán" span={1}>
              {caseData.payment_status === 'Chưa thanh toán' 
                ? <Tag color="red">Chưa thanh toán</Tag>
                : <Tag color="green">Đã thanh toán</Tag>
              }
            </Descriptions.Item>
            <Descriptions.Item label="Số chứng thư" span={1}>
              {caseData.certificate_number || 'Chưa có'}
            </Descriptions.Item>
            <Descriptions.Item label="Ngày chứng thư" span={1}>
              {caseData.certificate_date || 'Chưa có'}
            </Descriptions.Item>

            <Descriptions.Item label="Mã vận đơn" span={1}>
              {caseData.tracking_number || 'Chưa gửi chuyển phát'}
            </Descriptions.Item>
            <Descriptions.Item label="Nhân viên kinh doanh" span={1}>
              {caseData.business_staff || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Nhân viên thẩm định" span={1}>
              {caseData.valuation_staff || 'N/A'}
            </Descriptions.Item>

            <Descriptions.Item label="Kiểm soát viên" span={1}>
              {caseData.controller || 'N/A'}
            </Descriptions.Item>
            <Descriptions.Item label="Ghi chú pháp lý" span={2}>
              {caseData.legal_note || 'N/A'}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )
    },
    {
      key: 'documents',
      label: (
        <span>
          <FileTextOutlined />
          Tài liệu & Văn bản
        </span>
      ),
      children: <CaseDocuments caseData={caseData} onCaseRefresh={fetchCaseData} />
    },
    {
      key: 'tasks',
      label: (
        <span>
          <CheckSquareOutlined />
          Danh sách công việc liên quan
        </span>
      ),
      children: (
        <Card
          title="Danh sách công việc liên quan"
          extra={
            <Space wrap>
              <Button onClick={() => navigate('/cases')}>
                Vào Quản lý hồ sơ
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setTaskModalOpen(true)}
              >
                Tạo công việc mới
              </Button>
            </Space>
          }
          style={{ borderRadius: 10, border: '1px solid #e5e7eb' }}
        >
          <List
            loading={loadingTasks}
            dataSource={relatedTasks}
            locale={{ emptyText: <Empty description="Chưa có công việc nào liên quan đến hồ sơ này." /> }}
            renderItem={(task) => (
              <List.Item
                actions={[
                  <Link key="open-case" to={`/cases/${task.case_id || id}`}>
                    Mở hồ sơ
                  </Link>
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space wrap>
                      <strong>{task.title}</strong>
                      {getTaskStatusTag(task.status)}
                      {getTaskPriorityTag(task.priority)}
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={4}>
                      <span>{task.description || 'Không có mô tả'}</span>
                      <span style={{ color: '#64748b', fontSize: 12 }}>
                        Hạn chót: {formatTaskDueDate(task.due_date)}
                      </span>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )
    },
    {
      key: 'notes',
      label: (
        <span>
          <CommentOutlined />
          Ghi chú nội bộ
        </span>
      ),
      children: (
        <Card title="Nhật ký ghi chú hồ sơ" style={{ borderRadius: 10, border: '1px solid #e5e7eb' }}>
          <div style={{ marginBottom: 20 }}>
            <Input.TextArea
              rows={4}
              value={newNoteText}
              onChange={(e) => setNewNoteText(e.target.value)}
              placeholder="Nhập ghi chú mới tại đây..."
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleAddNote}
              loading={submittingNote}
              disabled={!newNoteText.trim()}
              style={{ marginTop: 12, borderRadius: 6, float: 'right' }}
            >
              Thêm ghi chú
            </Button>
            <div style={{ clear: 'both' }} />
          </div>

          <Divider style={{ margin: '16px 0' }} />

          <List
            loading={loadingNotes}
            itemLayout="horizontal"
            dataSource={notes}
            locale={{ emptyText: 'Chưa có ghi chú nào cho hồ sơ này.' }}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={<strong>Hệ thống / Người dùng</strong>}
                  description={
                    <div>
                      <p style={{ color: '#374151', fontSize: 14, margin: '4px 0' }}>{item.note}</p>
                      <span style={{ color: '#8c8c8c', fontSize: 12 }}>
                        {item.created_at ? new Date(item.created_at).toLocaleString('vi-VN') : ''}
                      </span>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Breadcrumbs and navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Breadcrumb separator=">">
          <Breadcrumb.Item><Link to="/dashboard">Dashboard</Link></Breadcrumb.Item>
          <Breadcrumb.Item><Link to="/cases">Hồ sơ</Link></Breadcrumb.Item>
          <Breadcrumb.Item>Chi tiết</Breadcrumb.Item>
        </Breadcrumb>
        <Button 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate('/cases')}
          style={{ borderRadius: 6 }}
        >
          Quay lại
        </Button>
      </div>

      {/* Case Header Card */}
      <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <Space direction="vertical" size={2}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 20, fontWeight: 700 }}>Hồ sơ: {caseData.customer_info || 'N/A'}</span>
              {getStatusTag(caseData.case_status)}
            </div>
            <span style={{ color: '#595959' }}>Số hợp đồng: <strong>{caseData.contract_number || 'Chưa có'}</strong></span>
          </Space>

          <Button 
            type="primary"
            icon={<EditOutlined />}
            onClick={() => setEditModalOpen(true)}
            style={{ borderRadius: 6 }}
          >
            Chỉnh sửa hồ sơ
          </Button>
        </div>
      </Card>

      {/* Main Tabs */}
      <Tabs defaultActiveKey="info" items={tabItems} size="large" />

      {/* Edit Modal */}
      <CaseEditModal 
        open={editModalOpen}
        caseData={caseData}
        filterOptions={{}} // Will be fetched internally or handled
        onClose={() => setEditModalOpen(false)}
        onSuccess={() => {
          setEditModalOpen(false);
          fetchCaseData();
        }}
      />

      <TaskModal
        open={taskModalOpen}
        defaultCaseId={Number(id)}
        onCancel={() => setTaskModalOpen(false)}
        onSubmit={handleCreateRelatedTask}
      />
    </div>
  );
}
