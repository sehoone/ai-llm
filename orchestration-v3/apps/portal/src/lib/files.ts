// 첨부 파일 검증·인코딩 (ADR-0014). 백엔드 지원 타입·상한과 일치.

export const ACCEPTED_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'text/plain',
  'text/markdown',
  'text/csv',
  'application/json',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // docx
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // xlsx
  'application/vnd.openxmlformats-officedocument.presentationml.presentation', // pptx
];

export const ACCEPT_ATTR = [...ACCEPTED_TYPES, '.md', '.csv', '.docx', '.xlsx', '.pptx'].join(',');

export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

/** 허용 여부 검사 — 통과면 null, 아니면 에러 메시지. type이 빈 경우(.md 등)는 확장자를 신뢰. */
export function validateFile(f: File): string | null {
  if (f.type && !ACCEPTED_TYPES.includes(f.type)) {
    return `지원하지 않는 파일 형식입니다: ${f.name}`;
  }
  if (f.size > MAX_FILE_SIZE) {
    return `${f.name}이(가) 10MB를 초과합니다`;
  }
  return null;
}

/** File → base64(접두어 제거). 전송용(ADR-0014 FileAttachment.data). */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1] ?? '');
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function isImageType(type: string): boolean {
  return type.startsWith('image/');
}
