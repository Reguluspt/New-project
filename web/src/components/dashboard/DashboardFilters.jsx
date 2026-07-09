import React from 'react';
import { Card, Select, Row, Col } from 'antd';

export default function DashboardFilters({ 
  filterOptions = {}, 
  filters = {}, 
  onFilterChange,
  monthOptions = [] 
}) {
  const { 
    years = [], 
    branches = [], 
    staff_names = [], 
    statuses = [], 
    customer_types = [] 
  } = filterOptions;

  const customerTypeLabels = {
    'individual': 'Cá nhân',
    'organization': 'Tổ chức'
  };

  const handleChange = (key, value) => {
    onFilterChange({
      ...filters,
      [key]: value
    });
  };

  const labelStyle = { 
    fontWeight: 600, 
    marginBottom: 6, 
    color: '#475569', 
    fontSize: 13,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  };

  return (
    <Card 
      style={{ marginBottom: 20, borderRadius: 12, border: '1px solid #d8e7e5' }} 
      bodyStyle={{ padding: '16px 20px' }}
    >
      <Row gutter={[12, 12]} align="middle">
        <Col xs={24} sm={12} md={4}>
          <div style={labelStyle}>Năm thống kê</div>
          <Select
            style={{ width: '100%' }}
            value={filters.year || undefined}
            onChange={(val) => handleChange('year', val)}
            options={years.map(y => ({ label: y, value: y }))}
          />
        </Col>
        <Col xs={24} sm={12} md={4}>
          <div style={labelStyle}>Nguồn/ngân hàng</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            value={filters.branch || ''}
            onChange={(val) => handleChange('branch', val)}
            options={[
              { label: 'Tất cả', value: '' },
              ...branches.map(b => ({ label: b, value: b }))
            ]}
          />
        </Col>
        <Col xs={24} sm={12} md={4}>
          <div style={labelStyle}>Loại khách hàng</div>
          <Select
            style={{ width: '100%' }}
            value={filters.customer_type || ''}
            onChange={(val) => handleChange('customer_type', val)}
            options={[
              { label: 'Tất cả', value: '' },
              ...customer_types.map(ct => ({ label: customerTypeLabels[ct] || ct, value: ct }))
            ]}
          />
        </Col>
        <Col xs={24} sm={12} md={4}>
          <div style={labelStyle}>Chuyên viên kinh doanh</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            value={filters.staff_name || ''}
            onChange={(val) => handleChange('staff_name', val)}
            options={[
              { label: 'Tất cả', value: '' },
              ...staff_names.map(s => ({ label: s, value: s }))
            ]}
          />
        </Col>
        <Col xs={24} sm={12} md={4}>
          <div style={labelStyle}>Trạng thái hồ sơ</div>
          <Select
            style={{ width: '100%' }}
            value={filters.status || ''}
            onChange={(val) => handleChange('status', val)}
            options={[
              { label: 'Tất cả', value: '' },
              ...statuses.map(s => ({ label: s, value: s }))
            ]}
          />
        </Col>
        <Col xs={24} sm={12} md={4}>
          <div style={labelStyle}>Tháng theo dõi</div>
          <Select
            style={{ width: '100%' }}
            value={filters.month || undefined}
            onChange={(val) => handleChange('month', val)}
            options={monthOptions.map(m => ({ label: m, value: m }))}
          />
        </Col>
      </Row>
    </Card>
  );
}

