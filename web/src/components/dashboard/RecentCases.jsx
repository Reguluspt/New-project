import React from 'react';
import { Card, Table, Tag, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;

export default function RecentCases({ data = [] }) {
  const navigate = useNavigate();

  const getStatusTag = (status) => {
    switch (status) {
      case 'Hoàn thành':
        return <Tag color="success">Hoàn thành</Tag>;
      case 'Đang thực hiện':
      case 'Đang xử lý':
        return <Tag color="warning">Đang thực hiện</Tag>;
      case 'Đã phát hành':
        return <Tag color="processing">Đã phát hành</Tag>;
      case 'Hủy':
        return <Tag color="error">Hủy</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  const getPaymentTag = (paymentStatus) => {
    return paymentStatus === 'Chưa thanh toán' 
      ? <Tag color="red">Chưa thu</Tag>
      : <Tag color="green">Đã thu</Tag>;
  };

  const columns = [
    {
      title: 'STT',
      key: 'index',
      width: 60,
      align: 'center',
      render: (text, record, index) => index + 1,
    },
    {
      title: 'Số HĐ',
      dataIndex: 'contract_number',
      key: 'contract_number',
      fontWeight: 'bold',
      render: (text) => <strong style={{ color: '#007f7a' }}>{text || 'N/A'}</strong>,
    },
    {
      title: 'Khách hàng',
      dataIndex: 'customer_info',
      key: 'customer_info',
      ellipsis: true,
    },
    {
      title: 'Tháng TH',
      dataIndex: 'execution_month',
      key: 'execution_month',
      width: 100,
      align: 'center',
    },
    {
      title: 'Phí thẩm định',
      dataIndex: 'valuation_fee',
      key: 'valuation_fee',
      align: 'right',
      render: (val) => val ? `${val.toLocaleString('vi-VN')} ?` : '0 ?',
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      align: 'center',
      render: (status) => getStatusTag(status),
    },
    {
      title: 'Thanh toán',
      dataIndex: 'payment_status',
      key: 'payment_status',
      width: 120,
      align: 'center',
      render: (payment) => getPaymentTag(payment),
    },
  ];

  return (
    <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5' }}>
      <Title level={4} style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>
        Hồ sơ thực hiện gần đây
      </Title>
      <Table
        size="small"
        columns={columns}
        dataSource={data}
        rowKey="case_id"
        pagination={false}
        onRow={(record) => ({
          onClick: () => {
            navigate(`/cases?id=${record.case_id}`);
          },
          style: { cursor: 'pointer' }
        })}
      />
    </Card>
  );
}
