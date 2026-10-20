import api from './axios'

export type MeetingStatus =
  | 'UPLOADED'
  | 'TRANSCRIBING'
  | 'TRANSCRIBED'
  | 'SUMMARIZING'
  | 'COMPLETED'
  | 'SAVED'
  | 'FAILED'

export interface MeetingSummary {
  id: string
  title: string
  status: MeetingStatus
  audio_filename: string
  audio_duration_sec?: number | null
  language: string
  transcription_provider?: string | null
  artifact_id?: string | null
  public_token?: string | null
  error_message?: string | null
  created_at: string
  updated_at: string
}

export interface ActionItem {
  task: string
  owner?: string
  due?: string
}

export interface DiscussionItem {
  topic: string
  points?: string[]
  speakers?: string[]
}

export interface MinutesContent {
  title?: string
  attendees?: string[]
  agenda?: string[]
  discussion?: DiscussionItem[]
  decisions?: string[]
  action_items?: ActionItem[]
  summary?: string
  next_steps?: string[]
}

export interface MinutesResponse {
  summary: string
  content: MinutesContent
  model_used: string
  version: number
}

export interface MeetingDetail extends MeetingSummary {
  minutes?: MinutesResponse | null
}

export interface Segment {
  seq: number
  speaker_label: string
  speaker_name?: string | null
  start_ms: number
  end_ms: number
  text: string
}

export interface TranscriptResponse {
  meeting_id: string
  segments: Segment[]
}

export interface CreateMeetingParams {
  file: File | Blob
  filename?: string
  title?: string
  language?: string
}

export const meetingApi = {
  create: async (params: CreateMeetingParams): Promise<{ id: string; status: MeetingStatus }> => {
    const formData = new FormData()
    const filename = params.filename || (params.file instanceof File ? params.file.name : 'recording.webm')
    formData.append('file', params.file, filename)
    if (params.title) formData.append('title', params.title)
    if (params.language) formData.append('language', params.language)
    const res = await api.post('v1/meetings', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  list: async (): Promise<MeetingSummary[]> => {
    const res = await api.get<{ items: MeetingSummary[] }>('v1/meetings')
    return res.data.items
  },

  get: async (id: string): Promise<MeetingDetail> => {
    const res = await api.get<MeetingDetail>(`v1/meetings/${id}`)
    return res.data
  },

  getTranscript: async (id: string): Promise<TranscriptResponse> => {
    const res = await api.get<TranscriptResponse>(`v1/meetings/${id}/transcript`)
    return res.data
  },

  getAudioBlob: async (id: string): Promise<Blob> => {
    const res = await api.get(`v1/meetings/${id}/audio`, { responseType: 'blob' })
    return res.data as Blob
  },

  updateSpeakers: async (id: string, mapping: Record<string, string>) => {
    await api.patch(`v1/meetings/${id}/speakers`, { mapping })
  },

  updateMinutes: async (id: string, content: MinutesContent, summary?: string): Promise<MinutesResponse> => {
    const res = await api.patch<MinutesResponse>(`v1/meetings/${id}/minutes`, { content, summary })
    return res.data
  },

  regenerate: async (id: string): Promise<MinutesResponse> => {
    const res = await api.post<MinutesResponse>(`v1/meetings/${id}/regenerate`)
    return res.data
  },

  publish: async (id: string): Promise<{ public_token: string; artifact_id: string }> => {
    const res = await api.post(`v1/meetings/${id}/publish`)
    return res.data
  },

  remove: async (id: string) => {
    await api.delete(`v1/meetings/${id}`)
  },
}
