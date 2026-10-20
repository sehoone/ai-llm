/**
 * Tiny IndexedDB helper for crash/reload recovery of in-progress recordings.
 *
 * Audio chunks are appended as they arrive; a small meta record tracks state.
 * All calls are best-effort — if IndexedDB is unavailable the recorder still
 * works, just without recovery.
 */

const DB_NAME = 'meeting-recorder'
const DB_VERSION = 1
const CHUNKS = 'chunks'
const META = 'meta'
const META_KEY = 'current'

export interface RecorderMeta {
  status: 'recording' | 'paused' | 'stopped'
  mimeType: string
  elapsedMs: number
  updatedAt: number
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('indexedDB-unavailable'))
      return
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(CHUNKS)) db.createObjectStore(CHUNKS, { autoIncrement: true })
      if (!db.objectStoreNames.contains(META)) db.createObjectStore(META)
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

function tx<T>(store: string, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const t = db.transaction(store, mode)
        const req = fn(t.objectStore(store))
        req.onsuccess = () => resolve(req.result)
        req.onerror = () => reject(req.error)
        t.oncomplete = () => db.close()
      })
  )
}

export async function idbAddChunk(chunk: Blob): Promise<void> {
  try {
    await tx(CHUNKS, 'readwrite', (s) => s.add(chunk))
  } catch {
    // best-effort
  }
}

export async function idbGetChunks(): Promise<Blob[]> {
  try {
    return await tx<Blob[]>(CHUNKS, 'readonly', (s) => s.getAll() as IDBRequest<Blob[]>)
  } catch {
    return []
  }
}

export async function idbSetMeta(meta: RecorderMeta): Promise<void> {
  try {
    await tx(META, 'readwrite', (s) => s.put(meta, META_KEY))
  } catch {
    // best-effort
  }
}

export async function idbGetMeta(): Promise<RecorderMeta | null> {
  try {
    const m = await tx<RecorderMeta | undefined>(
      META,
      'readonly',
      (s) => s.get(META_KEY) as IDBRequest<RecorderMeta | undefined>
    )
    return m ?? null
  } catch {
    return null
  }
}

export async function idbClear(): Promise<void> {
  try {
    await tx(CHUNKS, 'readwrite', (s) => s.clear())
    await tx(META, 'readwrite', (s) => s.clear())
  } catch {
    // best-effort
  }
}
