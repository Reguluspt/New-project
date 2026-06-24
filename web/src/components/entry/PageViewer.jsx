import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Space, Typography, Tooltip } from 'antd';
import { 
  LeftOutlined, 
  RightOutlined, 
  ZoomInOutlined, 
  ZoomOutOutlined, 
  RotateRightOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { pageImageUrl } from '../../api/entry';

const { Text } = Typography;

export default function PageViewer({ uploadId, activeFile, currentPage, onPageChange, rotation, onRotationChange }) {
  const [zoom, setZoom] = useState(1);
  const [imgSize, setImgSize] = useState({ width: 560, height: 792 });
  const containerRef = useRef(null);
  
  const pageCount = activeFile?.pages || 0;
  const fileName = activeFile?.name || '';
  const thumbnails = activeFile?.thumbnails || [];

  const fitToContainer = () => {
    if (!containerRef.current) return;
    const containerWidth = containerRef.current.clientWidth - 40;
    const containerHeight = containerRef.current.clientHeight - 40;
    
    const scaleX = containerWidth / imgSize.width;
    const scaleY = containerHeight / imgSize.height;
    
    const fitScale = Math.min(scaleX, scaleY);
    const newZoom = Math.min(Math.max(fitScale, 0.4), 3);
    setZoom(Number(newZoom.toFixed(2)));
  };

  useEffect(() => {
    // Reset zoom and rotation when file changes
    setZoom(1);
  }, [activeFile]);

  useEffect(() => {
    fitToContainer();
  }, [imgSize, activeFile, currentPage]);

  useEffect(() => {
    window.addEventListener('resize', fitToContainer);
    return () => {
      window.removeEventListener('resize', fitToContainer);
    };
  }, [imgSize]);

  const handleImageLoad = (e) => {
    const { naturalWidth, naturalHeight } = e.target;
    if (naturalWidth && naturalHeight) {
      setImgSize({ width: 560, height: (560 * naturalHeight) / naturalWidth });
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < pageCount) {
      onPageChange(currentPage + 1);
    }
  };

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.2, 3));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.2, 0.5));
  };

  const handleRotate = () => {
    const nextRotation = (rotation + 90) % 360;
    onRotationChange(nextRotation);
  };

  if (!uploadId || !activeFile) {
    return (
      <Card 
        style={{ height: '600px', display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: 12, border: '1px solid #dbe3f3' }}
        bodyStyle={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}
      >
        <FileTextOutlined style={{ fontSize: 48, color: '#bfbfbf' }} />
        <Text type="secondary">Chưa có tài liệu được chọn để hiển thị.</Text>
      </Card>
    );
  }

  const activeImgUrl = pageImageUrl(uploadId, activeFile.file_id, currentPage, rotation);

  return (
    <Card
      style={{ borderRadius: 12, border: '1px solid #dbe3f3', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', minHeight: '600px', overflow: 'hidden' }}
      bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', height: '100%' }}
    >
      {/* Top Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 16px', borderBottom: '1px solid #e5e7eb', background: '#fcfcfc' }}>
        <Tooltip title={fileName}>
          <Text strong style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {fileName}
          </Text>
        </Tooltip>

        <Space size="small">
          <Button 
            icon={<LeftOutlined />} 
            onClick={handlePrevPage} 
            disabled={currentPage <= 1}
            size="small"
          />
          <Text style={{ fontSize: 13 }}>
            Trang {currentPage} / {pageCount}
          </Text>
          <Button 
            icon={<RightOutlined />} 
            onClick={handleNextPage} 
            disabled={currentPage >= pageCount}
            size="small"
          />
        </Space>

        <Space size="small">
          <Button 
            onClick={fitToContainer} 
            size="small"
            style={{ fontSize: 11 }}
            title="Tự động zoom để trang vừa khít khung"
          >
            Vừa khung
          </Button>
          <Button 
            icon={<ZoomOutOutlined />} 
            onClick={handleZoomOut} 
            size="small"
            title="Thu nhỏ"
          />
          <Text style={{ fontSize: 12, width: 35, textAlign: 'center' }}>
            {Math.round(zoom * 100)}%
          </Text>
          <Button 
            icon={<ZoomInOutlined />} 
            onClick={handleZoomIn} 
            size="small"
            title="Phóng to"
          />
          <Button 
            icon={<RotateRightOutlined />} 
            onClick={handleRotate} 
            size="small"
            title="Xoay trang"
          />
        </Space>
      </div>

      {/* Main Panel: Sidebar Thumbnails strip + Main Image Container */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Side Thumbnails */}
        <div style={{ width: 80, borderRight: '1px solid #e5e7eb', overflowY: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, padding: '12px 4px', background: '#fafafa' }}>
          {thumbnails.map((thumbUrl, idx) => {
            const pageIndex = idx + 1;
            const isActive = pageIndex === currentPage;
            // Load thumbnail at rotation 0 for preview
            const thumbSrc = pageImageUrl(uploadId, activeFile.file_id, pageIndex, 0);
            return (
              <div 
                key={pageIndex} 
                onClick={() => onPageChange(pageIndex)}
                style={{ 
                  width: 60, 
                  height: 80, 
                  border: isActive ? '2px solid #0f6cbd' : '1px solid #d9d9d9',
                  borderRadius: 4,
                  overflow: 'hidden',
                  cursor: 'pointer',
                  position: 'relative',
                  background: '#ffffff',
                  boxShadow: isActive ? '0 0 4px rgba(15,108,189,0.3)' : 'none'
                }}
              >
                <img 
                  src={thumbSrc} 
                  alt={`Trang ${pageIndex}`} 
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                />
                <div style={{ 
                  position: 'absolute', 
                  bottom: 0, 
                  left: 0, 
                  right: 0, 
                  background: isActive ? '#0f6cbd' : 'rgba(0,0,0,0.5)', 
                  color: '#ffffff', 
                  fontSize: 10, 
                  textAlign: 'center', 
                  padding: '1px 0' 
                }}>
                  Trang {pageIndex}
                </div>
              </div>
            );
          })}
        </div>

        {/* Center Main Image Canvas */}
        <div 
          ref={containerRef}
          style={{ flex: 1, overflow: 'auto', display: 'flex', justifyContent: 'center', alignItems: 'flex-start', padding: 20, background: '#f3f4f6' }}
        >
          <div style={{ 
            transform: `scale(${zoom})`, 
            transformOrigin: 'top center',
            transition: 'transform 0.15s ease',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)',
            background: '#ffffff',
            borderRadius: 4,
            overflow: 'hidden'
          }}>
            <img 
              src={activeImgUrl} 
              alt={`Tài liệu trang ${currentPage}`} 
              onLoad={handleImageLoad}
              style={{ display: 'block', maxWidth: '100%', height: 'auto', width: '560px' }} 
            />
          </div>
        </div>
      </div>
    </Card>
  );
}
