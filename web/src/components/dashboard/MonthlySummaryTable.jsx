import React from 'react';
import { Card, Table, Typography } from 'antd';
import { useResizableColumns } from '../../hooks/useResizableColumns';

const { Title } = Typography;

const formatNumber = (value) => {
  if (value === undefined || value === null) return "0";
  return Math.round(value).toLocaleString('vi-VN').replace(/,/g, '.');
};

export default function MonthlySummaryTable({ data = [] }) {
  const { getResizableProps } = useResizableColumns('monthly_summary', {
    month: 120,
    case_count: 100,
    projected: 160,
    paid: 160,
    unpaid: 160
  });

  const columns = [
    {
      title: 'Tháng',
      dataIndex: 'month',
      key: 'month',
      align: 'center',
      width: 120,
      render: (text) => <span>{text}</span>,
    },
    {
      title: 'Hồ sơ',
      dataIndex: 'case_count',
      key: 'case_count',
      align: 'right',
      width: 100,
      render: (val) => <span>{val}</span>,
    },
    {
      title: 'Dự kiến',
      dataIndex: 'projected',
      key: 'projected',
      align: 'right',
      width: 160,
      render: (val) => <span>{formatNumber(val)}</span>,
    },
    {
      title: 'Đã thu',
      dataIndex: 'paid',
      key: 'paid',
      align: 'right',
      width: 160,
      render: (val) => <span>{formatNumber(val)}</span>,
    },
    {
      title: 'Công nợ',
      dataIndex: 'unpaid',
      key: 'unpaid',
      align: 'right',
      width: 160,
      render: (val) => <span>{formatNumber(val)}</span>,
    },
  ];

  return (
    <Card 
      style={{ borderRadius: 12, border: '1px solid #dbe3f3', height: '100%' }}
      bodyStyle={{ padding: '20px 22px' }}
    >
      <Title level={4} style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>
        Tổng hợp theo tháng
      </Title>
      <Table
        size="small"
        {...getResizableProps(columns)}
        dataSource={data}
        rowKey="month"
        pagination={false}
        scroll={{ y: 260, x: 'max-content' }}
        style={{ border: '1px solid #f1f5f9', borderRadius: 8, overflow: 'hidden' }}
      />
    </Card>
  );
}

