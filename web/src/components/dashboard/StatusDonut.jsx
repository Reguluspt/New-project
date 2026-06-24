import React from 'react';
import { Card, Typography } from 'antd';

const { Title } = Typography;

export default function StatusDonut({ statusCounts = {} }) {
  const colors = {
    'Đang thực hiện': '#f59e0b',
    'Hoàn thành': '#10b981',
    'Đã phát hành': '#3b82f6',
    'Hủy': '#ef4444',
  };

  const total = Object.values(statusCounts).reduce((a, b) => a + b, 0);

  // Compute conic gradient string
  let accumulatedPercent = 0;
  const gradientParts = [];

  // Filter keys that exist in the colors mapping
  const statuses = Object.keys(colors);

  statuses.forEach((status) => {
    const count = statusCounts[status] || 0;
    if (count > 0 && total > 0) {
      const percent = (count / total) * 100;
      const color = colors[status];
      gradientParts.push(`${color} ${accumulatedPercent}% ${accumulatedPercent + percent}%`);
      accumulatedPercent += percent;
    }
  });

  const gradientString = gradientParts.length > 0
    ? `conic-gradient(${gradientParts.join(', ')})`
    : `conic-gradient(#e2e8f0 0% 100%)`;

  return (
    <Card style={{ borderRadius: 12, border: '1px solid #dbe3f3', height: '100%' }}>
      <Title level={4} style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
        Trạng thái hồ sơ
      </Title>

      {/* Donut Container */}
      <div style={{ position: 'relative', width: 200, height: 200, margin: '20px auto' }}>
        <div style={{
          width: 200,
          height: 200,
          borderRadius: '50%',
          background: gradientString,
          position: 'relative'
        }}>
          {/* Inner cutout hole */}
          <div style={{
            position: 'absolute',
            inset: 50,
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.05)'
          }}>
            <b style={{ fontSize: 26, fontWeight: 850, color: '#0f172a', lineHeight: 1 }}>{total}</b>
            <span style={{ fontSize: 12, color: '#64748b', fontWeight: 600, marginTop: 4 }}>Tổng hồ sơ</span>
          </div>
        </div>
      </div>

      {/* Custom Legend */}
      <div style={{ marginTop: 24, display: 'grid', gap: 10 }}>
        {statuses.map((status) => {
          const count = statusCounts[status] || 0;
          const color = colors[status];
          const percent = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';

          return (
            <div key={status} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: color }} />
                <span style={{ color: '#475569', fontWeight: 500 }}>{status}</span>
              </div>
              <div style={{ color: '#0f172a', fontWeight: 700 }}>
                {count} <span style={{ color: '#64748b', fontWeight: 400, fontSize: 11, marginLeft: 4 }}>({percent}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
