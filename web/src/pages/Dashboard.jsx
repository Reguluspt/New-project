import React, { useState, useEffect } from 'react';
import { Row, Col, Alert, Card, Skeleton } from 'antd';
import { useDashboard } from '../hooks/useDashboard';
import DashboardFilters from '../components/dashboard/DashboardFilters';
import KpiCards from '../components/dashboard/KpiCards';
import RevenueChart from '../components/dashboard/RevenueChart';
import MonthlySummaryTable from '../components/dashboard/MonthlySummaryTable';
import BankRevenueDonut from '../components/dashboard/BankRevenueDonut';
import UnpaidCasesTable from '../components/dashboard/UnpaidCasesTable';

export default function Dashboard() {
  const [filters, setFilters] = useState({
    year: new Date().getFullYear().toString(),
    branch: '',
    customer_type: '',
    staff_name: '',
    status: '',
    month: '',
  });

  const { stats, filterOptions, isLoading, isError, error } = useDashboard(filters);

  // Sync selected target month when year changes or initial stats load
  useEffect(() => {
    if (stats?.selected_month) {
      setFilters(prev => {
        const months = stats.monthly_revenue?.map(r => r.month) || [];
        // Only update if current month filter is blank or not valid for current options/year
        if (!prev.month || !months.includes(prev.month) || (prev.month.split('/')[1] !== prev.year)) {
          return {
            ...prev,
            month: stats.selected_month
          };
        }
        return prev;
      });
    }
  }, [stats?.selected_month, stats?.monthly_revenue]);

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
  };

  const monthOptions = stats?.monthly_revenue?.map(r => r.month) || [];

  if (isLoading && !stats) {
    return (
      <div style={{ padding: '0 0 24px 0' }}>
        {/* Filter Bar Skeleton */}
        <Card style={{ marginBottom: 20, borderRadius: 12 }}>
          <Skeleton.Input active style={{ width: '100%' }} />
        </Card>
        {/* KPI Cards Skeleton */}
        <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
          {[1, 2, 3, 4].map(i => (
            <Col key={i} xs={24} sm={12} md={6}>
              <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5' }}>
                <Skeleton active paragraph={{ rows: 2 }} />
              </Card>
            </Col>
          ))}
        </Row>
        {/* Charts Skeleton */}
        <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
          <Col xs={24} lg={12}>
            <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5' }}>
              <Skeleton active paragraph={{ rows: 6 }} />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5' }}>
              <Skeleton active paragraph={{ rows: 6 }} />
            </Card>
          </Col>
        </Row>
      </div>
    );
  }

  if (isError) {
    return (
      <Alert
        message="Lỗi tải dữ liệu"
        description={error?.message || "Đã xảy ra lỗi khi kết nối đến server."}
        type="error"
        showIcon
        style={{ margin: 20 }}
      />
    );
  }

  return (
    <div style={{ padding: '0 0 24px 0' }}>
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <h1 style={{ fontSize: 32, fontWeight: 760, color: '#0f172a', margin: 0 }}>Dashboard</h1>
        <svg style={{ width: 20, height: 20, color: '#94a3b8', cursor: 'pointer' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
        </svg>
      </div>
      <div style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>
        Theo dõi doanh thu dự kiến, thanh toán, công nợ và tỷ lệ doanh thu theo hệ thống ngân hàng.
      </div>

      {/* Filters Bar */}
      <DashboardFilters 
        filterOptions={filterOptions} 
        filters={filters} 
        onFilterChange={handleFilterChange} 
        monthOptions={monthOptions}
      />

      {/* KPI Cards */}
      <KpiCards stats={stats} />

      {/* Charts & Summary Table Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={12}>
          <RevenueChart data={stats?.monthly_revenue || []} />
        </Col>
        <Col xs={24} lg={12}>
          <MonthlySummaryTable data={stats?.monthly_revenue || []} />
        </Col>
      </Row>

      {/* Bank Donut & Detailed Unpaid Cases Row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <BankRevenueDonut data={stats?.bank_revenue || []} />
        </Col>
        <Col xs={24} lg={12}>
          <UnpaidCasesTable 
            data={stats?.unpaid_cases || []} 
            unpaidTotal={stats?.unpaid_total || 0}
            unpaidCount={stats?.unpaid_count || 0}
            selectedMonth={filters.month || stats?.selected_month || ''}
          />
        </Col>
      </Row>
    </div>
  );
}

