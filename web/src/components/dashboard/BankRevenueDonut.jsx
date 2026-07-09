import React from 'react';
import { Card, Row, Col, Typography } from 'antd';

const { Title } = Typography;

const formatMillion = (value) => {
  if (value === undefined || value === null) return "0";
  const million = Math.round(value / 1000000);
  return million.toLocaleString('vi-VN').replace(/,/g, '.');
};

export default function BankRevenueDonut({ data = [] }) {
const colors = [
    "#007f7a",
    "#2aa0a4",
    "#d99a55",
    "#047857",
    "#c2413d",
    "#6aa6a1",
    "#b77938",
    "#64748b",
    "#94a3b8",
    "#0f766e",
];

  const total = data.reduce((sum, item) => sum + item.value, 0);

  // Compute conic gradient string
  let accumulatedPercent = 0;
  const gradientParts = [];

  data.forEach((item, index) => {
    if (item.value > 0 && total > 0) {
      const percent = (item.value / total) * 100;
      const color = colors[index % colors.length];
      gradientParts.push(`${color} ${accumulatedPercent.toFixed(2)}% ${(accumulatedPercent + percent).toFixed(2)}%`);
      accumulatedPercent += percent;
    }
  });

  const gradientString = gradientParts.length > 0
    ? `conic-gradient(${gradientParts.join(', ')})`
    : `conic-gradient(#e2e8f0 0% 100%)`;

  return (
    <Card 
      style={{ borderRadius: 12, border: '1px solid #d8e7e5', height: '100%' }}
      bodyStyle={{ padding: '20px 22px' }}
    >
      <Title level={4} style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
        Tỷ lệ doanh thu theo ngân hàng
      </Title>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 20 }}>
        Tổng doanh thu dự kiến trong năm theo bộ lọc hiện tại.
      </div>

      {total <= 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748b' }}>
          Chưa có dữ liệu doanh thu theo ngân hàng trong năm đang chọn.
        </div>
      ) : (
        <Row gutter={[16, 16]} align="middle" style={{ minHeight: 220 }}>
          <Col xs={24} sm={10} style={{ display: 'flex', justifyContent: 'center' }}>
            {/* Donut Container */}
            <div style={{ position: 'relative', width: 170, height: 170 }}>
              <div style={{
                width: 170,
                height: 170,
                borderRadius: '50%',
                background: gradientString,
                position: 'relative'
              }}>
                {/* Inner cutout hole */}
                <div style={{
                  position: 'absolute',
                  inset: 42,
                  borderRadius: '50%',
                  backgroundColor: '#ffffff',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.05)'
                }}>
                  <b style={{ fontSize: 22, fontWeight: 850, color: '#0f172a', lineHeight: 1.1 }}>
                    {formatMillion(total)}
                  </b>
                  <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginTop: 4 }}>
                    Tổng Tr
                  </span>
                </div>
              </div>
            </div>
          </Col>

          <Col xs={24} sm={14}>
            {/* Custom Legend */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {data.map((item, index) => {
                const color = colors[index % colors.length];
                return (
                  <div 
                    key={item.bank} 
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'space-between', 
                      fontSize: 12 
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                      <div style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: color, flexShrink: 0 }} />
                      <span 
                        style={{ 
                          color: '#475569', 
                          fontWeight: 500, 
                          textOverflow: 'ellipsis', 
                          overflow: 'hidden', 
                          whiteSpace: 'nowrap' 
                        }}
                        title={item.bank}
                      >
                        {item.bank}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0 }}>
                      <span style={{ color: '#64748b', fontWeight: 600 }}>
                        {formatMillion(item.value)} Tr
                      </span>
                      <span style={{ color: '#0f172a', fontWeight: 700, width: 45, textAlign: 'right' }}>
                        {item.percent}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Col>
        </Row>
      )}
    </Card>
  );
}
