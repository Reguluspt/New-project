const IMAGE_FILE_PATTERN = /\.(png|jpe?g|webp)$/i;

export const isMergedImageSource = (file, files = []) => (
  files.some((candidate) => candidate.merged_from_images)
  && IMAGE_FILE_PATTERN.test(String(file?.name || ''))
);

export const initialScanStatus = (file, files = []) => (
  isMergedImageSource(file, files) ? 'skipped' : 'pending'
);
