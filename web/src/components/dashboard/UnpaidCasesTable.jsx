import React from 'react';
import { Card, Table, Typography } from 'antd';
import { useResizableColumns } from '../../hooks/useResizableColumns';

const { Title } = Typography;

const formatNumber = (value) => {
  if (value === undefined || value === null) return "0";
  return Math.round(value).toLocaleString('vi-VN').replace(/,/g, '.');
};

export default function UnpaidCasesTable({ 
  data = [], 
  unpaidTotal = 0, 
  unpaidCount = 0, 
  selectedMonth = '' 
}) {
  const { getResizableProps } = useResizableColumns('unpaid_cases', {
    contract_number: 140,
    customer_info: 400,
    source: 200,
    valuation_fee_number: 120
  });

  const columns = [
    {
      title: 'Số HS',
      dataIndex: 'contract_number',
      key: 'contract_number',
      width: 140,
      render: (text) => <strong>{text || 'N/A'}</strong>,
    },
    {
      title: 'Khách hàng',
      dataIndex: 'customer_info',
      key: 'customer_info',
      width: 400,
      ellipsis: true,
    },
    {
      title: 'Ngân hàng',
      dataIndex: 'source',
      key: 'source',
      width: 200,
      ellipsis: true,
    },
    {
      title: 'Còn lại',
      dataIndex: 'valuation_fee_number',
      key: 'valuation_fee_number',
      align: 'right',
      width: 120,
      render: (val) => <span>{formatNumber(val)}</span>,
    },
  ];

  return (
    <Card 
      style={{ borderRadius: 12, border: '1px solid #dbe3f3', height: '100%' }}
      bodyStyle={{ padding: '20px 22px' }}
    >
      <Title level={4} style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
        Báo cáo công nợ chi tiết ({selectedMonth})
      </Title>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
        Số hồ sơ chưa thanh toán: {unpaidCount} | Tổng công nợ: {formatNumber(unpaidTotal)}
      </div>
      <Table
        size="small"
        {...getResizableProps(columns)}
        dataSource={data}
        rowKey={(record, idx) => `${record.contract_number}-${idx}`}
        pagination={false}
        scroll={{ y: 260, x: 'max-content' }}
        style={{ border: '1px solid #f1f5f9', borderRadius: 8, overflow: 'hidden' }}
      />
    </Card>
  );
}

