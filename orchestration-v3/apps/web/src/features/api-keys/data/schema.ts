import { z } from 'zod'

export const apiKeySchema = z.object({
  id: z.number(),
  name: z.string(),
  key: z.string(),
  isActive: z.boolean(),
  expiresAt: z.string().nullable().optional(),
  createdAt: z.string(),
})

export type ApiKey = z.infer<typeof apiKeySchema>
