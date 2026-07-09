import React, { useState, useEffect } from 'react';
import { Card, Input, Select, Button, Space, Row, Col, Badge } from 'antd';
import { SearchOutlined, ClearOutlined } from '@ant-design/icons';
import { getFilters } from '../../api/cases';

export default function CaseFilterBar({ filterOptions = {}, filters = {}, onFilterChange }) {
  const [internalFilters, setInternalFilters] = useState({});

  useEffect(() => {
    getFilters()
      .then(res => {
        setInternalFilters(res.data || {});
      })
      .catch(err => {
        console.error("Error fetching filters in CaseFilterBar:", err);
      });
  }, []);

  const {
    statuses = [],
    branches = [],
    valuation_branches = [],
    appraisers = [],
    execution_months = [],
    payment_statuses = []
  } = { ...internalFilters, ...filterOptions };

  const [searchText, setSearchText] = useState(filters.search || '');

  // Debounce search text changes
  useEffect(() => {
    const handler = setTimeout(() => {
      if (filters.search !== searchText) {
        onFilterChange({ ...filters, search: searchText });
      }
    }, 300);

    return () => clearTimeout(handler);
  }, [searchText]);

  // Sync internal search state when filters are cleared externally
  useEffect(() => {
    setSearchText(filters.search || '');
  }, [filters.search]);

  const handleChange = (key, value) => {
    onFilterChange({
      ...filters,
      [key]: value || ''
    });
  };

  const handleClear = () => {
    setSearchText('');
    onFilterChange({
      page: 1,
      size: filters.size || 20,
      sort: filters.sort || 'id',
      order: filters.order || 'desc',
      search: '',
      status: '',
      branch: '',
      valuation_branch: '',
      appraiser_name: '',
      execution_month: '',
      payment_status: ''
    });
  };

  const hasActiveFilters = 
    filters.search || 
    filters.status || 
    filters.branch || 
    filters.valuation_branch || 
    filters.appraiser_name || 
    filters.execution_month || 
    filters.payment_status;

  return (
    <Card 
      style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #d8e7e5' }} 
      bodyStyle={{ padding: '16px 20px' }}
    >
      <Row gutter={[16, 16]} align="middle">
        <Col xs={24} md={8}>
          <Input
            placeholder="Tìm kiếm hồ sơ (Số HĐ, khách hàng, địa chỉ, ghi chú...)"
            prefix={<SearchOutlined style={{ color: '#94a3b8' }} />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
            style={{ width: '100%', borderRadius: 8 }}
          />
        </Col>
        
        <Col xs={24} md={16}>
          <Space wrap size="small" style={{ width: '100%', justifyContent: 'flex-end' }}>
            {/* Status Filter */}
            <Select
              style={{ width: 140 }}
              placeholder="Trạng thái"
              allowClear
              value={filters.status || undefined}
              onChange={(val) => handleChange('status', val)}
              options={['Đang xử lý', 'Hoàn thành', 'Hủy'].map(s => ({ label: s, value: s }))}
            />

            {/* Branch Filter */}
            <Select
              style={{ width: 220 }}
              placeholder="Nguồn / Ngân hàng"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.branch || undefined}
              onChange={(val) => handleChange('branch', val)}
              options={branches.map(b => ({ label: b, value: b }))}
            />

            {/* Valuation Branch Filter */}
            <Select
              style={{ width: 180 }}
              placeholder="Chi nhánh thẩm định"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.valuation_branch || undefined}
              onChange={(val) => handleChange('valuation_branch', val)}
              options={valuation_branches.map(vb => ({ label: vb, value: vb }))}
            />

            {/* Appraiser Filter */}
            <Select
              style={{ width: 140 }}
              placeholder="Người thẩm định"
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.appraiser_name || undefined}
              onChange={(val) => handleChange('appraiser_name', val)}
              options={appraisers.map(a => ({ label: a, value: a }))}
            />

            {/* Execution Month Filter */}
            <Select
              style={{ width: 130 }}
              placeholder="Tháng thực hiện"
              allowClear
              value={filters.execution_month || undefined}
              onChange={(val) => handleChange('execution_month', val)}
              options={execution_months.map(m => ({ label: m, value: m }))}
            />

            {/* Payment Filter */}
            <Select
              style={{ width: 130 }}
              placeholder="Thanh toán"
              allowClear
              value={filters.payment_status || undefined}
              onChange={(val) => handleChange('payment_status', val)}
              options={payment_statuses.map(p => ({ label: p, value: p }))}
            />

            {hasActiveFilters && (
              <Button 
                type="dashed" 
                danger 
                icon={<ClearOutlined />} 
                onClick={handleClear}
                style={{ borderRadius: 6 }}
              >
                Xóa bộ lọc
              </Button>
            )}
          </Space>
        </Col>
      </Row>
    </Card>
  );
}
