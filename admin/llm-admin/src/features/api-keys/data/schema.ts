import { z } from 'zod'

export const apiKeySchema = z.object({
  id: z.number(),
  user_id: z.number(),
  key: z.string(),
  name: z.string(),
  is_active: z.boolean(),
  created_at: z.string(),
  expires_at: z.string().nullable().optional(),
})

export type ApiKey = z.infer<typeof apiKeySchema>
