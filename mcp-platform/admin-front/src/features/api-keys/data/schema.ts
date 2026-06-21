import { z } from 'zod'

export const apiKeySchema = z.object({
  id: z.number(),
  name: z.string(),
  key: z.string(),
  isActive: z.boolean(),
  expiresAt: z.string().nullable().optional(),
  createdAt: z.string(),
  lastUsedAt: z.string().nullable().optional(),
  usageCount: z.number().default(0),
})

export type ApiKey = z.infer<typeof apiKeySchema>
