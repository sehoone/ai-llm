import { z } from 'zod'

const userStatusSchema = z.union([
  z.literal('active'),
  z.literal('inactive'),
])
export type UserStatus = z.infer<typeof userStatusSchema>

export const userSchema = z.object({
  id: z.union([z.string(), z.number()]),
  username: z.string(),
  email: z.string(),
  status: userStatusSchema,
  role: z.string(),          // platform-server returns uppercase (USER, ADMIN, etc.)
  createdAt: z.coerce.date().optional(),
})
export type User = z.infer<typeof userSchema>
