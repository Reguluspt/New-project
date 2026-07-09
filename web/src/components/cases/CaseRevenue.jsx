import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Select, Space, Spin, Alert, Modal, Button, Form, Input, DatePicker, Tag, message } from 'antd';
import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { MailOutlined, DollarCircleOutlined, SaveOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { getStats } from '../../api/dashboard';
import { listCases, updatePayment, addNote, remindPayment, updateStatus } from '../../api/cases';
import { getFilters } from '../../api/cases';
import { useResizableColumns } from '../../hooks/useResizableColumns';
import moment from 'moment';

const COLORS = ['#007f7a', '#047857', '#c2413d', '#d98a2b', '#d99a55'];

export default function CaseRevenue() {
  const { getResizableProps } = useResizableColumns('case_revenue_table', {
    contract_number: 140,
    customer_info: 240,
    execution_month: 120,
    valuation_fee_number: 140,
    payment_status: 120,
    action: 120
  });

  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    year: new Date().getFullYear().toString(),
    branch: '',
    execution_month: ''
  });
  
  const [filterOptions, setFilterOptions] = useState({});
  const [stats, setStats] = useState(null);
  const [casesList, setCasesList] = useState([]);
  const [pieGroupCriteria, setPieGroupCriteria] = useState('bank');

  // Modals state
  const [selectedCase, setSelectedCase] = useState(null);

  const [reminderModalVisible, setReminderModalVisible] = useState(false);
  const [reminderForm] = Form.useForm();
  const [sendingReminder, setSendingReminder] = useState(false);

  const [detailModalVisible, setDetailModalVisible] = useState(false);

  // Fetch filter options once
  useEffect(() => {
    getFilters().then(res => {
      setFilterOptions(res.data || {});
    }).catch(err => console.error(err));
  }, []);

  // Fetch stats and cases on filter change
  const fetchData = async () => {
    setLoading(true);
    try {
      const statsRes = await getStats({
        year: filters.year,
        branch: filters.branch,
        month: filters.execution_month
      });
      setStats(statsRes.data);

      const casesRes = await listCases({
        page: 1,
        size: 50,
        year: filters.year,
        branch: filters.branch,
        execution_month: filters.execution_month,
        payment_status: 'Chưa thanh toán',
        exclude_status: 'Hủy',
        sort: 'valuation_fee',
        order: 'desc'
      });
      setCasesList(casesRes.data?.items || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filters]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value || ''
    }));
  };

  const handleCancelCase = (record) => {
    Modal.confirm({
      title: 'Xác nhận hủy hồ sơ',
      content: `Bạn có chắc chắn muốn hủy hồ sơ của khách hàng ${record.customer_info || 'N/A'} (HĐ số: ${record.contract_number || 'N/A'})? Hồ sơ bị hủy sẽ không được tính vào báo cáo công nợ.`,
      okText: 'Xác nhận hủy',
      okType: 'danger',
      cancelText: 'Quay lại',
      onOk: async () => {
        try {
          await updateStatus(record.id, 'Hủy');
          message.success('Đã hủy hồ sơ thành công!');
          fetchData();
        } catch (err) {
          console.error(err);
          message.error('Lỗi khi hủy hồ sơ');
        }
      }
    });
  };

  const handleTogglePaymentStatus = async (record) => {
    const nextStatus = record.payment_status === 'Chưa thanh toán' ? 'Đã thanh toán' : 'Chưa thanh toán';
    try {
      await updatePayment(record.id, nextStatus);
      if (nextStatus === 'Đã thanh toán') {
        const dateStr = moment().format('DD/MM/YYYY');
        await addNote(record.id, `Đã thu phí ngày: ${dateStr}`);
      }
      message.success(`Đã chuyển trạng thái sang: ${nextStatus === 'Đã thanh toán' ? 'Đã thu' : 'Chưa thu'}`);
      fetchData();
    } catch (err) {
      console.error(err);
      message.error('Lỗi cập nhật trạng thái thanh toán');
    }
  };

  const formatCurrency = (val) => {
    return (val || 0).toLocaleString('vi-VN') + ' ?';
  };

  const formatMillion = (val) => {
    return `${Math.round((val || 0) / 1000000).toLocaleString('vi-VN')} tr`;
  };

  const getMonthDifference = (execMonthStr) => {
    if (!execMonthStr || !execMonthStr.includes('/')) return 99;
    const [m, y] = execMonthStr.split('/').map(Number);
    const currentYear = new Date().getFullYear();
    const currentMonth = new Date().getMonth() + 1;
    return (currentYear - y) * 12 + (currentMonth - m);
  };

  const getPieData = () => {
    if (!stats?.unpaid_cases || stats.unpaid_cases.length === 0) return [];
    
    if (pieGroupCriteria === 'bank') {
      const groups = {};
      stats.unpaid_cases.forEach(c => {
        const bank = c.source ? c.source.split(' - ')[0].trim() : 'Khác';
        groups[bank] = (groups[bank] || 0) + (c.valuation_fee_number || 0);
      });
      const data = Object.entries(groups).map(([name, value]) => ({ name, value }));
      data.sort((a, b) => b.value - a.value);
      if (data.length > 5) {
        const top = data.slice(0, 4);
        const othersVal = data.slice(4).reduce((sum, item) => sum + item.value, 0);
        top.push({ name: 'Khác', value: othersVal });
        return top;
      }
      return data;
    } else if (pieGroupCriteria === 'customer_type') {
      const groups = { 'Cá nhân': 0, 'Tổ chức': 0 };
      stats.unpaid_cases.forEach(c => {
        const label = c.customer_type === 'organization' ? 'Tổ chức' : 'Cá nhân';
        groups[label] = (groups[label] || 0) + (c.valuation_fee_number || 0);
      });
      return Object.entries(groups).map(([name, value]) => ({ name, value })).filter(item => item.value > 0);
    } else if (pieGroupCriteria === 'aging') {
      const groups = { 'Dưới 30 ngày': 0, '30 - 90 ngày': 0, 'Trên 90 ngày': 0 };
      stats.unpaid_cases.forEach(c => {
        const diff = getMonthDifference(c.execution_month);
        if (diff <= 0) {
          groups['Dưới 30 ngày'] += (c.valuation_fee_number || 0);
        } else if (diff <= 2) {
          groups['30 - 90 ngày'] += (c.valuation_fee_number || 0);
        } else {
          groups['Trên 90 ngày'] += (c.valuation_fee_number || 0);
        }
      });
      return Object.entries(groups).map(([name, value]) => ({ name, value })).filter(item => item.value > 0);
    }
    return [];
  };

  // Open Reminder Mail Modal
  const handleOpenReminderModal = (record) => {
    setSelectedCase(record);
    
    const subject = `[NHẮC NỢ] Yêu cầu thanh toán phí thẩm định dịch vụ - HĐ số: ${record.contract_number}`;
    const body = `Kính gửi Quý đối tác / Khách hàng,
 
CÔNG TY CỔ PHẦN THẨM ĐỊNH GIÁ THẾ KỶ - CHI NHÁNH TẠI TP HỒ CHÍ MINH xin gửi lời chào trân trọng đến Quý khách hàng.
 
Chúng tôi xin thông báo về khoản phí dịch vụ thẩm định giá cho hồ sơ của Quý khách hàng như sau:
- Khách hàng: ${record.customer_info || 'N/A'}
- Số hợp đồng: ${record.contract_number || 'N/A'}
- Phí dịch vụ thẩm định: ${formatCurrency(record.valuation_fee_number)}
 
Để thuận tiện cho việc đối chiếu và thanh toán, Quý khách hàng vui lòng chuyển khoản thanh toán phí dịch vụ thẩm định về số tài khoản thụ hưởng sau:
 
- Chủ tài khoản: CÔNG TY CỔ PHẦN THẨM ĐỊNH GIÁ THẾ KỶ - CN TẠI TP HỒ CHÍ MINH.
- Số tài khoản: 0531002471549
- Tại Ngân hàng: Vietcombank (VCB) Chi nhánh Đông Sài Gòn.
 
Quý khách hàng vui lòng ghi rõ nội dung chuyển khoản: "Thanh toan phi tham dinh HD ${record.contract_number || ''}".
Sau khi thực hiện chuyển khoản, Quý khách vui lòng gửi lại hình ảnh sao kê/biên nhận chuyển khoản để chúng tôi xác nhận và xuất hóa đơn.
 
Mọi thắc mắc vui lòng liên hệ trực tiếp để được giải đáp.
Trân trọng cảm ơn sự hợp tác của Quý khách.`;

    reminderForm.setFieldsValue({
      to_email: '',
      subject: subject,
      body: body
    });
    setReminderModalVisible(true);
  };

  const handleSendReminder = async () => {
    try {
      const values = await reminderForm.validateFields();
      setSendingReminder(true);
      await remindPayment(selectedCase.id, values);
      message.success('Đã gửi email nhắc nợ thành công!');
      setReminderModalVisible(false);
      fetchData(); // reload to get the log note in case list if needed
    } catch (err) {
      console.error(err);
      message.error('Gửi email nhắc nợ thất bại: ' + (err.response?.data?.error || err.message));
    } finally {
      setSendingReminder(false);
    }
  };

  const handleOpenDetailModal = (record) => {
    setSelectedCase(record);
    setDetailModalVisible(true);
  };

  const columns = [
    {
      title: 'Số HĐ',
      dataIndex: 'contract_number',
      key: 'contract_number',
      render: (text, record) => (
        <a 
          style={{ fontWeight: 'bold', color: '#007f7a' }} 
          onClick={() => handleOpenDetailModal(record)}
        >
          {text || 'N/A'}
        </a>
      ),
    },
    {
      title: 'Khách hàng',
      dataIndex: 'customer_info',
      key: 'customer_info',
      ellipsis: true,
      render: (text, record) => (
        <a 
          style={{ color: '#1e293b', fontWeight: 500, cursor: 'pointer' }} 
          onClick={() => handleOpenDetailModal(record)}
        >
          {text || 'N/A'}
        </a>
      ),
    },
    {
      title: 'Tháng thực hiện',
      dataIndex: 'execution_month',
      key: 'execution_month',
      align: 'center',
    },
    {
      title: 'Phí thẩm định',
      dataIndex: 'valuation_fee_number',
      key: 'valuation_fee_number',
      align: 'right',
      render: (val) => formatCurrency(val),
    },
    {
      title: 'Trạng thái thu',
      dataIndex: 'payment_status',
      key: 'payment_status',
      align: 'center',
      render: (val, record) => val === 'Chưa thanh toán' 
        ? <Tag color="error" style={{ cursor: 'pointer', fontWeight: 600 }} onClick={() => handleTogglePaymentStatus(record)}>Chưa thu</Tag>
        : <Tag color="success" style={{ cursor: 'pointer', fontWeight: 600 }} onClick={() => handleTogglePaymentStatus(record)}>Đã thu</Tag>,
    },
    {
      title: 'Hành động',
      key: 'action',
      align: 'center',
      render: (_, record) => (
        <Space size="small">
          <Button 
            type="link" 
            icon={<MailOutlined />} 
            size="small"
            onClick={() => handleOpenReminderModal(record)}
            disabled={record.payment_status === 'Đã thanh toán'}
            style={{ padding: 0 }}
          >
            Nhắc nợ
          </Button>
          <Button 
            type="link" 
            danger
            size="small"
            onClick={() => handleCancelCase(record)}
            style={{ padding: 0 }}
          >
            Hủy
          </Button>
        </Space>
      ),
    },
  ];
  const resizableProps = getResizableProps(columns);

  if (loading && !stats) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <Spin size="large" tip="Đang tải báo cáo doanh thu..." />
      </div>
    );
  }

  const chartData = (stats?.monthly_revenue || []).map(r => ({
    month: `T${r.month.split('/')[0]}`,
    'Dự kiến': r.projected,
    'Đã thu': r.paid,
    'Công nợ': r.unpaid
  }));

  const pieData = getPieData();

  return (
    <div>
      {/* Filters bar */}
      <Card style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #d8e7e5' }} bodyStyle={{ padding: 14 }}>
        <Space wrap size="middle">
          <div>
            <span style={{ marginRight: 8, fontWeight: 600 }}>Năm:</span>
            <Select
              style={{ width: 120 }}
              value={filters.year}
              onChange={(v) => handleFilterChange('year', v)}
              options={(filterOptions.years || [new Date().getFullYear().toString()]).map(y => ({ label: y, value: y }))}
            />
          </div>
          <div>
            <span style={{ marginRight: 8, fontWeight: 600 }}>Tháng TH:</span>
            <Select
              style={{ width: 140 }}
              placeholder="Tất cả tháng"
              allowClear
              value={filters.execution_month || undefined}
              onChange={(v) => handleFilterChange('execution_month', v)}
              options={(filterOptions.execution_months || []).map(m => ({ label: m, value: m }))}
            />
          </div>
          <div>
            <span style={{ marginRight: 8, fontWeight: 600 }}>Chi nhánh/Ngân hàng:</span>
            <Select
              style={{ width: 200 }}
              placeholder="Tất cả nguồn"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.branch || undefined}
              onChange={(v) => handleFilterChange('branch', v)}
              options={(filterOptions.branches || []).map(b => ({ label: b, value: b }))}
            />
          </div>
        </Space>
      </Card>

      {/* Statistic Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5', background: 'linear-gradient(135deg, #effaf8 0%, #d7f0ed 100%)' }}>
            <Statistic
              title="Tổng doanh thu dự kiến"
              value={formatMillion(stats?.year_projected)}
              valueStyle={{ color: '#007f7a', fontWeight: 750 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5', background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)' }}>
            <Statistic
              title="Đã thanh toán (Đã thu)"
              value={formatMillion(stats?.year_paid)}
              valueStyle={{ color: '#047857', fontWeight: 750 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5', background: 'linear-gradient(135deg, #fff5f5 0%, #ffe4e6 100%)' }}>
            <Statistic
              title="Công nợ tồn đọng"
              value={formatMillion(stats?.year_unpaid)}
              valueStyle={{ color: '#be123c', fontWeight: 750 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5', background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)' }}>
            <Statistic
              title="Số lượng hồ sơ"
              value={stats?.total_cases || 0}
              valueStyle={{ color: '#0f172a', fontWeight: 750 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts & Table */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={14}>
          <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5', height: '100%' }} title="Biểu đồ doanh thu thực hiện">
            <div style={{ width: '100%', height: 350 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
                  <YAxis tickFormatter={(v) => `${(v / 1000000).toFixed(0)}m`} stroke="#64748b" fontSize={12} />
                  <Tooltip formatter={(value, name) => [formatCurrency(value), name]} />
                  <Legend />
                  <Bar dataKey="Đã thu" stackId="a" fill="#047857" barSize={35} />
                  <Bar dataKey="Công nợ" stackId="a" fill="#c2413d" barSize={35} />
                  <Line type="monotone" dataKey="Dự kiến" stroke="#007f7a" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
        
        {/* Pie Chart analysis */}
        <Col xs={24} lg={10}>
          <Card 
            style={{ borderRadius: 12, border: '1px solid #d8e7e5', height: '100%' }} 
            title="Phân tích cơ cấu công nợ"
            extra={
              <Select 
                value={pieGroupCriteria} 
                onChange={setPieGroupCriteria} 
                style={{ width: 180 }}
                size="small"
              >
                <Select.Option value="bank">Theo ngân hàng</Select.Option>
                <Select.Option value="customer_type">Theo đối tượng</Select.Option>
                <Select.Option value="aging">Theo tuổi nợ</Select.Option>
              </Select>
            }
          >
            {pieData.length > 0 ? (
              <div style={{ width: '100%', height: 300, display: 'flex', flexDirection: 'column', justifyItems: 'center', alignItems: 'center' }}>
                <ResponsiveContainer width="100%" height={230}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={pieData.length === 1 ? 0 : 3}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value, name) => [formatCurrency(value), name]} />
                  </PieChart>
                </ResponsiveContainer>
                {/* Legend list */}
                <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '8px 16px', fontSize: '11px', marginTop: 10 }}>
                  {pieData.map((entry, index) => (
                    <span key={entry.name} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: COLORS[index % COLORS.length] }}></span>
                      {entry.name}: {formatCurrency(entry.value)}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center', color: '#64748b' }}>
                Không có dữ liệu công nợ
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5' }} title="Chi tiết công nợ chưa thu lớn nhất">
            <Table
              size="small"
              columns={resizableProps.columns}
              components={resizableProps.components}
              dataSource={casesList}
              rowKey="id"
              pagination={{ defaultPageSize: 50, showSizeChanger: true, pageSizeOptions: ['10', '20', '50', '100'] }}
              style={{ tableLayout: 'fixed' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Reminder Mail Modal */}
      <Modal
        title={
          <Space>
            <MailOutlined style={{ color: '#007f7a' }} />
            <span>Soạn thảo email nhắc nợ tự động</span>
          </Space>
        }
        open={reminderModalVisible}
        onOk={handleSendReminder}
        onCancel={() => setReminderModalVisible(false)}
        confirmLoading={sendingReminder}
        okText="Gửi email nhắc nợ"
        cancelText="Đóng"
        width={750}
        destroyOnClose
      >
        <Form form={reminderForm} layout="vertical">
          <Form.Item 
            name="to_email" 
            label="Email người nhận" 
            rules={[{ required: true, type: 'email', message: 'Vui lòng nhập email người nhận hợp lệ' }]}
            tooltip="Nhập email của Khách hàng hoặc Cán bộ ngân hàng để gửi thư nhắc phí."
          >
            <Input placeholder="nhap-email@example.com" />
          </Form.Item>
          
          <Form.Item name="subject" label="Tiêu đề Email" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item name="body" label="Nội dung nhắc nợ" rules={[{ required: true }]}>
            <Input.TextArea rows={12} />
          </Form.Item>
        </Form>
      </Modal>
      {/* Detail Case Modal */}
      <Modal
        title="Thông tin chi tiết hồ sơ"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Đóng
          </Button>
        ]}
        width={600}
        destroyOnClose
      >
        {selectedCase && (
          <div style={{ padding: '8px 0' }}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ color: '#64748b', fontSize: '12px', display: 'block' }}>Số hợp đồng</span>
                  <Space align="center" wrap>
                    <strong style={{ fontSize: '16px', color: '#007f7a' }}>{selectedCase.contract_number || 'N/A'}</strong>
                    {selectedCase.customer_type === 'organization' ? <Tag color="blue">Tổ chức</Tag> : <Tag color="orange">Cá nhân</Tag>}
                  </Space>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ color: '#64748b', fontSize: '12px', display: 'block' }}>Phí thẩm định</span>
                  <strong style={{ fontSize: '18px', color: '#be123c' }}>{formatCurrency(selectedCase.valuation_fee_number)}</strong>
                </div>
              </Col>
              <Col span={24}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ color: '#64748b', fontSize: '12px', display: 'block' }}>Tên khách hàng</span>
                  <span style={{ fontWeight: 700, fontSize: '15px', color: '#1e293b' }}>{selectedCase.customer_info || 'N/A'}</span>
                </div>
              </Col>
              <Col span={24}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ color: '#64748b', fontSize: '12px', display: 'block' }}>Địa chỉ khách hàng</span>
                  <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: 6, border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap', color: '#334155' }}>
                    {selectedCase.customer_address || 'N/A'}
                  </div>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ color: '#64748b', fontSize: '12px', display: 'block' }}>Nguồn</span>
                  <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: 6, border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap', color: '#334155' }}>
                    {selectedCase.source || 'N/A'}
                  </div>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ color: '#64748b', fontSize: '12px', display: 'block' }}>Ngày tạo</span>
                  <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: 6, border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap', color: '#334155' }}>
                    {selectedCase.created_at ? moment(selectedCase.created_at).format('DD/MM/YYYY') : 'N/A'}
                  </div>
                </div>
              </Col>
              <Col span={24}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ color: '#64748b', fontSize: '12px', display: 'block' }}>Mục đích thẩm định giá</span>
                  <span style={{ color: '#334155' }}>{selectedCase.valuation_purpose || 'N/A'}</span>
                </div>
              </Col>
              <Col span={24}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ color: '#64748b', fontSize: '12px', display: 'block' }}>Tài sản thẩm định</span>
                  <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: 6, border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap', color: '#334155' }}>
                    {selectedCase.asset_description || 'N/A'}
                  </div>
                </div>
              </Col>
              <Col span={24}>
                <div style={{ marginBottom: 12 }}>
                  <span style={{ color: '#64748b', fontSize: '12px', display: 'block' }}>Ghi chú cá nhân</span>
                  <div style={{ background: '#fffbeb', padding: '8px 12px', borderRadius: 6, border: '1px solid #fef3c7', whiteSpace: 'pre-wrap', color: '#334155' }}>
                    {selectedCase.personal_note || 'N/A'}
                  </div>
                </div>
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  );
}
