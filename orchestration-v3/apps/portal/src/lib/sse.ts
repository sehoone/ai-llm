// fetch 응답 본문(ReadableStream)에서 event-SSE 프레임을 파싱한다(ADR-0011).
// 프레임 구분은 빈 줄(\n\n), 각 프레임은 `event:`/`data:` 라인으로 구성. data는 JSON 우선 파싱.

type OnEvent = (event: string, data: unknown) => void;

export async function readSSE(response: Response, onEvent: OnEvent): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  let buffer = '';

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      dispatchFrame(frame, onEvent);
    }
  }
  if (buffer.trim()) dispatchFrame(buffer, onEvent);
}

function dispatchFrame(frame: string, onEvent: OnEvent): void {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
  }
  if (dataLines.length === 0) return;
  const raw = dataLines.join('\n');
  let data: unknown = raw;
  try {
    data = JSON.parse(raw);
  } catch {
    /* data를 문자열 그대로 둔다 */
  }
  onEvent(event, data);
}
