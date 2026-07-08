import { z } from "zod"

export const llmResourceSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, { message: "Name is required" }),
  resourceType: z.enum(["chat", "embedding"]).default("chat"),
  modelName: z.string().optional(),
  provider: z.string().min(1, { message: "Provider is required" }),
  apiBase: z.string().url({ message: "Invalid URL" }),
  // apiKey: 생성/수정 폼에서만 사용, 서버 응답에는 포함되지 않음 (보안). 빈 문자열은 undefined로 취급.
  apiKey: z.string().optional().transform(v => (v === '' ? undefined : v)),
  deploymentName: z.string().optional(),
  apiVersion: z.string().optional(),
  region: z.string().optional(),
  priority: z.coerce.number().default(0),
  weight: z.coerce.number().min(1).default(1),
  isActive: z.boolean().default(true),
})

export type LLMResource = z.infer<typeof llmResourceSchema>
