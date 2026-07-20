export const deliveryMailFailureNotice = (error) => {
  const apiError = error?.response?.data?.error;
  if (typeof apiError === 'string' && apiError.trim()) {
    return {
      type: 'error',
      title: 'Gửi mail phát hành chứng thư thất bại',
      content: apiError,
    };
  }

  return {
    type: 'warning',
    title: 'Chưa xác nhận được trạng thái gửi mail',
    content: (
      'Kết nối tới máy chủ bị gián đoạn trong khi gửi. '
      + 'Vui lòng kiểm tra Hộp thư đã gửi trước khi thử lại để tránh gửi trùng.'
    ),
  };
};
