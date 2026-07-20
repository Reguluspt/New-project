import test from 'node:test';
import assert from 'node:assert/strict';
import { initialScanStatus, isMergedImageSource } from './ocrQueue.js';

test('skips source images when the upload contains a merged image PDF', () => {
  const files = [
    { name: 'GCN_anh_ghep.pdf', merged_from_images: true },
    { name: 'front.jpg' },
    { name: 'back.PNG' },
  ];

  assert.equal(initialScanStatus(files[0], files), 'pending');
  assert.equal(initialScanStatus(files[1], files), 'skipped');
  assert.equal(initialScanStatus(files[2], files), 'skipped');
});

test('keeps images pending when no merged PDF exists', () => {
  const files = [{ name: 'single.webp' }];

  assert.equal(initialScanStatus(files[0], files), 'pending');
  assert.equal(isMergedImageSource(files[0], files), false);
});

test('keeps unrelated PDFs pending alongside a merged image PDF', () => {
  const files = [
    { name: 'GCN_anh_ghep.pdf', merged_from_images: true },
    { name: 'attachment.pdf' },
    { name: 'front.jpeg' },
  ];

  assert.equal(initialScanStatus(files[1], files), 'pending');
  assert.equal(initialScanStatus(files[2], files), 'skipped');
});
