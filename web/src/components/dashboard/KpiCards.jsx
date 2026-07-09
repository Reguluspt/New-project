import React from 'react';
import { Row, Col, Progress } from 'antd';

const formatMillion = (value) => {
  if (value === undefined || value === null) return "0";
  const million = Math.round(value / 1000000);
  return million.toLocaleString('vi-VN').replace(/,/g, '.');
};

export default function KpiCards({ stats = {} }) {
  const {
    year_projected = 0,
    year_paid = 0,
    year_unpaid = 0,
    month_projected = 0,
    selected_month = ''
  } = stats;

  const paid_ratio = year_projected <= 0 ? 0 : Math.min(100, Math.round((year_paid / year_projected) * 100));
  const monthly_target = Math.max(year_projected / 12, 1);
  const target_ratio = month_projected <= 0 ? 0 : Math.min(100, Math.round((month_projected / monthly_target) * 100));

  const cardStyle = {
    borderRadius: 12,
    border: '1px solid #d8e7e5',
    padding: '20px 22px',
    background: '#ffffff',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
    position: 'relative'
  };

  const primaryCardStyle = {
    ...cardStyle,
    background: '#006b67',
    color: '#ffffff',
    borderColor: '#006b67',
    overflow: 'hidden',
  };

  const labelStyle = {
    color: '#64748b',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    marginBottom: 8
  };

  const primaryLabelStyle = {
    ...labelStyle,
    color: 'rgba(255, 255, 255, 0.75)'
  };

  const valueStyle = {
    fontSize: 28,
    fontWeight: 800,
    color: '#0f172a',
    lineHeight: 1.1,
    marginBottom: 16
  };

  const primaryValueStyle = {
    ...valueStyle,
    color: '#ffffff'
  };

  const unitStyle = {
    fontSize: 15,
    fontWeight: 500,
    color: '#64748b',
    marginLeft: 2
  };

  const primaryUnitStyle = {
    ...unitStyle,
    color: 'rgba(255, 255, 255, 0.75)'
  };

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
      {/* Card 1 */}
      <Col xs={24} sm={12} md={6}>
        <div style={cardStyle}>
          <div style={labelStyle}>Doanh thu dự kiến cả năm</div>
          <div style={valueStyle}>
            {formatMillion(year_projected)}<span style={unitStyle}> Tr</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, marginTop: 'auto' }}>
            <svg style={{ width: 14, height: 14, color: '#007f7a' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M3 17l6-6 4 4 8-8M21 13V7h-6" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span style={{ color: '#64748b' }}>Dữ liệu theo bộ lọc hiện tại</span>
          </div>
        </div>
      </Col>

      {/* Card 2 */}
      <Col xs={24} sm={12} md={6}>
        <div style={cardStyle}>
          <div style={labelStyle}>Đã thanh toán cả năm</div>
          <div style={valueStyle}>
            {formatMillion(year_paid)}<span style={unitStyle}> Tr</span>
          </div>
          <div style={{ width: '100%', marginTop: 'auto' }}>
            <Progress 
              percent={paid_ratio} 
              size="small" 
              strokeColor="#047857" 
              trailColor="#f1f5f9"
              showInfo={false}
              style={{ margin: 0, height: 6 }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', fontSize: 12, color: '#64748b', marginTop: 4 }}>
              Tỷ lệ thu: {paid_ratio}%
            </div>
          </div>
        </div>
      </Col>

      {/* Card 3 */}
      <Col xs={24} sm={12} md={6}>
        <div style={cardStyle}>
          <div style={labelStyle}>Công nợ tồn cả năm</div>
          <div style={valueStyle}>
            {formatMillion(year_unpaid)}<span style={unitStyle}> Tr</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, marginTop: 'auto' }}>
            <svg style={{ width: 14, height: 14, color: '#c2413d' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span style={{ color: '#64748b' }}>Không tính hồ sơ trạng thái Hủy</span>
          </div>
        </div>
      </Col>

      {/* Card 4 */}
      <Col xs={24} sm={12} md={6}>
        <div style={primaryCardStyle}>
          {/* Dollar Watermark Icon */}
          <svg style={{ position: 'absolute', right: -12, bottom: -12, width: 96, height: 96, opacity: 0.12, fill: '#ffffff' }} viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1.41 12.09c-1.9.31-2.42-.91-2.5-1.54h2.18c.09.28.37.58.91.58.46 0 .82-.19.82-.57 0-.32-.23-.52-.89-.73l-1.07-.34c-1.3-.41-2-.99-2-2.13 0-1.17.96-2.02 2.34-2.22V6h2v1.14c1.64.26 2.16 1.25 2.2 1.76h-2.1c-.04-.15-.22-.64-.84-.64-.53 0-.74.3-.74.5 0 .28.27.46.82.63l1.02.32c1.4.44 2.06 1.07 2.06 2.2 0 1.23-.9 2.02-2.44 2.18V15h-2v-1.91z"/>
          </svg>

          <div style={primaryLabelStyle}>Doanh thu dự kiến trong tháng</div>
          <div style={primaryValueStyle}>
            {formatMillion(month_projected)}<span style={primaryUnitStyle}> Tr</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginTop: 'auto', zIndex: 2 }}>
            <span style={{ fontSize: 12, color: 'rgba(255, 255, 255, 0.8)' }}>Tháng {selected_month || '--'}</span>
            <div 
              style={{ 
                backgroundColor: '#ffffff', 
                color: '#006b67', 
                fontWeight: 700, 
                borderRadius: 12, 
                fontSize: 11,
                padding: '3px 10px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
              }}
            >
              Đạt {target_ratio}% Target
            </div>
          </div>
        </div>
      </Col>
    </Row>
  );
}

