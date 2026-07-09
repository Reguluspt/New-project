import React from 'react';
import { Card, Typography } from 'antd';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const { Title } = Typography;

export default function RevenueChart({ data = [] }) {
  const formatCurrency = (val) => {
    return val.toLocaleString('vi-VN') + ' ₫';
  };

  const formatYAxis = (val) => {
    if (val >= 1000000000) {
      return (val / 1000000000).toFixed(1) + ' Tỷ';
    }
    if (val >= 1000000) {
      return (val / 1000000).toFixed(0) + ' Tr';
    }
    return val;
  };

  return (
    <Card style={{ borderRadius: 12, border: '1px solid #d8e7e5', height: '100%' }}>
      <Title level={4} style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
        Doanh thu vs Công nợ hàng tháng
      </Title>
      <div style={{ width: '100%', height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 10, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis 
              dataKey="month" 
              stroke="#64748b" 
              fontSize={12}
            />
            <YAxis 
              tickFormatter={formatYAxis} 
              stroke="#64748b" 
              fontSize={12}
            />
            <Tooltip 
              formatter={(value) => [formatCurrency(value), '']}
              labelFormatter={(label) => `Tháng ${label}`}
              contentStyle={{ borderRadius: 8, border: '1px solid #d8e7e5', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
            />
            <Legend verticalAlign="top" height={36} />
            <Bar 
              name="Công nợ" 
              dataKey="unpaid" 
              fill="#c2413d" 
              radius={[4, 4, 0, 0]} 
            />
            <Bar 
              name="Doanh thu" 
              dataKey="projected" 
              fill="#007f7a" 
              radius={[4, 4, 0, 0]} 
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
