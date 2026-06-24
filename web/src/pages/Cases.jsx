import React, { useState, useEffect } from 'react';
import { Card, Tabs } from 'antd';
import CaseTable from '../components/cases/CaseTable';
import CaseRevenue from '../components/cases/CaseRevenue';
import { getFilters } from '../api/cases';

export default function Cases() {
  const [filterOptions, setFilterOptions] = useState({});

  const fetchFilters = () => {
    getFilters()
      .then((res) => {
        setFilterOptions(res.data || {});
      })
      .catch((err) => console.error('Error fetching filter options:', err));
  };

  useEffect(() => {
    fetchFilters();
  }, []);

  const tabItems = [
    {
      key: 'cases_list',
      label: 'Quản lý hồ sơ',
      children: <CaseTable filterOptions={filterOptions} onFilterOptionsRefresh={fetchFilters} />,
    },
    {
      key: 'revenue_analytics',
      label: 'Quản lý công nợ',
      children: <CaseRevenue />,
    },
  ];

  return (
    <Card 
      style={{ borderRadius: 12, border: 'none', boxShadow: '0 1px 3px rgba(0,0,0,0.02)' }}
      styles={{ body: { padding: '8px 16px' } }}
    >
      <Tabs defaultActiveKey="cases_list" items={tabItems} />
    </Card>
  );
}
