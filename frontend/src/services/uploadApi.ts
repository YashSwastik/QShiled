import api from './api';

export interface ScanResult {
  id: string;
  status: 'completed' | 'failed' | string;
  file_count: number;
  finding_count: number;
  upload_name: string;
  upload_type: string;
  error_message: string | null;
}

export async function uploadScan(
  applicationId: string,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<ScanResult> {
  const formData = new FormData();
  formData.append('application_id', applicationId);
  formData.append('file', file);

  const response = await api.post<ScanResult>('/api/scans/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (event.total) {
        onProgress?.(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return response.data;
}
