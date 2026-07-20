import test from 'node:test';
import assert from 'node:assert/strict';
import { deliveryMailFailureNotice } from './deliveryMailError.js';

test('shows the backend error when the API returns a structured failure', () => {
  const notice = deliveryMailFailureNotice({
    response: { data: { error: 'Không tìm thấy mail gốc' } },
  });

  assert.equal(notice.type, 'error');
  assert.equal(notice.content, 'Không tìm thấy mail gốc');
});

test('uses an indeterminate warning for a dropped connection', () => {
  const notice = deliveryMailFailureNotice({ code: 'ERR_NETWORK' });

  assert.equal(notice.type, 'warning');
  assert.match(notice.content, /kiểm tra Hộp thư đã gửi/i);
});

test('uses an indeterminate warning for an HTML gateway error', () => {
  const notice = deliveryMailFailureNotice({
    response: { status: 502, data: '<html>Bad Gateway</html>' },
  });

  assert.equal(notice.type, 'warning');
  assert.match(notice.content, /tránh gửi trùng/i);
});
