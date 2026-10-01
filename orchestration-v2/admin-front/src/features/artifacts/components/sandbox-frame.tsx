'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

import { AlertTriangle } from 'lucide-react'

/**
 * Renders untrusted artifact content inside a locked-down iframe.
 *
 * Security model:
 * - `sandbox="allow-scripts"` WITHOUT `allow-same-origin` → the document runs in
 *   a unique opaque origin and cannot read the parent's cookies, storage or DOM.
 * - A `<meta http-equiv="Content-Security-Policy">` inside the document blocks all
 *   network access (`connect-src 'none'`) and restricts scripts/styles to a small
 *   set of public CDNs, so an artifact cannot exfiltrate data or call back to the app.
 * - Runtime errors are relayed to the parent via `postMessage` for a friendly overlay.
 */

const ALLOWED_SCRIPT_CDNS = [
  'https://cdnjs.cloudflare.com',
  'https://unpkg.com',
  'https://cdn.jsdelivr.net',
  'https://cdn.tailwindcss.com',
  'https://code.jquery.com',
].join(' ')

const CSP = [
  "default-src 'none'",
  `script-src 'unsafe-inline' 'unsafe-eval' ${ALLOWED_SCRIPT_CDNS}`,
  "style-src 'unsafe-inline' https://fonts.googleapis.com",
  'font-src https://fonts.gstatic.com',
  'img-src data: blob:',
  "connect-src 'none'",
].join('; ')

const ERROR_RELAY = `
  window.onerror = function (message) {
    parent.postMessage({ __artifact_error: String(message) }, '*');
    return false;
  };
  window.addEventListener('unhandledrejection', function (e) {
    parent.postMessage({ __artifact_error: String(e.reason) }, '*');
  });
  (function () {
    // artifactData SDK — persist/read user input via the trusted host bridge.
    // The sandbox has no network access; the host performs the actual API call.
    var _pending = {};
    window.addEventListener('message', function (e) {
      var d = e.data || {};
      if (d.__artifact_data_reply && d.id && _pending[d.id]) {
        if (d.error) { _pending[d.id].reject(new Error(d.error)); }
        else { _pending[d.id].resolve(d.data); }
        delete _pending[d.id];
      }
    });
    function call(kind, payload) {
      return new Promise(function (resolve, reject) {
        var id = Math.random().toString(36).slice(2) + Date.now();
        _pending[id] = { resolve: resolve, reject: reject };
        var msg = { __artifact_data: kind, id: id };
        if (payload) { for (var k in payload) { msg[k] = payload[k]; } }
        parent.postMessage(msg, '*');
      });
    }
    window.artifactData = {
      get: function () { return call('get'); },
      set: function (data) { return call('set', { data: data }); }
    };
  })();
`

/** Strip ES module syntax so the code can run under Babel-standalone's IIFE wrapper. */
function prepareReactCode(code: string): string {
  return code
    .replace(/^\s*import\s.+$/gm, '') // drop import lines (CSP blocks them anyway)
    .replace(/export\s+default\s+/, 'return ')
    .replace(/export\s+/g, '')
}

function buildSrcDoc(type: string, content: string): string {
  const head = `<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="${CSP}"><meta name="viewport" content="width=device-width, initial-scale=1">`
  const base = `<style>html,body{margin:0;padding:0;font-family:system-ui,-apple-system,sans-serif;background:#fff;color:#111}body{padding:12px;box-sizing:border-box}</style>`

  switch (type) {
    case 'image/svg+xml':
      return `<!doctype html><html><head>${head}${base}<style>svg{max-width:100%;height:auto}</style></head><body><script>${ERROR_RELAY}</script>${content}</body></html>`

    case 'application/vnd.mermaid':
      return `<!doctype html><html><head>${head}${base}</head><body><script>${ERROR_RELAY}</script>
<div class="mermaid">${content}</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>try{mermaid.initialize({startOnLoad:true,securityLevel:'strict'})}catch(e){parent.postMessage({__artifact_error:String(e)},'*')}</script>
</body></html>`

    case 'application/vnd.react':
      return `<!doctype html><html><head>${head}
<script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
${base}</head><body><div id="root"></div>
<script>${ERROR_RELAY}</script>
<script type="text/babel" data-presets="react">
try {
  const __Comp = (function () { ${prepareReactCode(content)} })();
  const __root = ReactDOM.createRoot(document.getElementById('root'));
  __root.render(React.createElement(__Comp));
} catch (e) {
  parent.postMessage({ __artifact_error: String(e && e.message ? e.message : e) }, '*');
}
</script>
</body></html>`

    case 'text/html':
    default:
      // If the content is already a full document, inject CSP + error relay into <head>;
      // otherwise wrap the fragment in a minimal document.
      if (/<html[\s>]/i.test(content)) {
        if (/<head[\s>]/i.test(content)) {
          return content.replace(/<head([^>]*)>/i, `<head$1>${head}<script>${ERROR_RELAY}</script>`)
        }
        return content.replace(/<html([^>]*)>/i, `<html$1><head>${head}<script>${ERROR_RELAY}</script></head>`)
      }
      return `<!doctype html><html><head>${head}${base}</head><body><script>${ERROR_RELAY}</script>${content}</body></html>`
  }
}

type DataRecord = Record<string, unknown>

interface SandboxFrameProps {
  type: string
  content: string
  className?: string
  /** Read persisted interactive data (host performs the API call). */
  dataGet?: () => Promise<DataRecord>
  /** Persist interactive data (host performs the API call). */
  dataSet?: (data: DataRecord) => Promise<void>
}

export function SandboxFrame({ type, content, className, dataGet, dataSet }: SandboxFrameProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  // Errors are tagged with the document they came from, so an error from a
  // previous render is never shown against newly-rendered content (no effect
  // needed to clear stale state).
  const [error, setError] = useState<{ doc: string; msg: string } | null>(null)

  const srcDoc = useMemo(() => buildSrcDoc(type, content), [type, content])
  const srcDocRef = useRef(srcDoc)
  useEffect(() => {
    srcDocRef.current = srcDoc
  }, [srcDoc])

  // Keep latest data handlers in refs so the message listener stays stable.
  const dataGetRef = useRef(dataGet)
  const dataSetRef = useRef(dataSet)
  useEffect(() => {
    dataGetRef.current = dataGet
    dataSetRef.current = dataSet
  }, [dataGet, dataSet])

  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      if (e.source !== iframeRef.current?.contentWindow) return
      const data = e.data as {
        __artifact_error?: string
        __artifact_data?: 'get' | 'set'
        id?: string
        data?: DataRecord
      }
      if (!data) return

      if (typeof data.__artifact_error === 'string') {
        setError({ doc: srcDocRef.current, msg: data.__artifact_error })
        return
      }

      // artifactData bridge: run the host-side API call and reply into the iframe.
      if (data.__artifact_data && data.id) {
        const win = iframeRef.current?.contentWindow
        const reply = (payload: { data?: DataRecord; error?: string }) =>
          win?.postMessage({ __artifact_data_reply: true, id: data.id, ...payload }, '*')
        if (data.__artifact_data === 'get') {
          const run = dataGetRef.current?.()
          // No reader wired up → treat as empty rather than an error.
          if (!run) return reply({ data: {} })
          run
            .then((result) => reply({ data: (result as DataRecord) ?? {} }))
            .catch((err) => reply({ error: String(err?.message ?? err) }))
        } else {
          const run = dataSetRef.current?.(data.data ?? {})
          if (!run) return reply({ error: '이 화면에서는 저장할 수 없습니다' })
          run
            .then(() => reply({ data: data.data ?? {} }))
            .catch((err) => reply({ error: String(err?.message ?? err) }))
        }
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

  const activeError = error && error.doc === srcDoc ? error.msg : null

  return (
    <div className={`relative h-full w-full ${className ?? ''}`}>
      <iframe
        ref={iframeRef}
        title='artifact-preview'
        sandbox='allow-scripts'
        srcDoc={srcDoc}
        className='h-full w-full border-0 bg-white'
      />
      {activeError && (
        <div className='absolute inset-x-0 bottom-0 flex items-start gap-2 border-t border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive'>
          <AlertTriangle className='mt-0.5 h-3.5 w-3.5 shrink-0' />
          <span className='break-words'>{activeError}</span>
        </div>
      )}
    </div>
  )
}
