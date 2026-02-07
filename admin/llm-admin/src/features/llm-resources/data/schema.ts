import { z } from "zod"

export const llmResourceSchema = z.object({
  id: z.number().optional(),
  name: z.string().min(1, { message: "Name is required" }),
  provider: z.string().min(1, { message: "Provider is required" }),
  api_base: z.string().url({ message: "Invalid URL" }),
  api_key: z.string().min(1, { message: "API Key is required" }),
  deployment_name: z.string().optional(),
  api_version: z.string().optional(),
  region: z.string().optional(),
  priority: z.coerce.number().default(0),
  is_active: z.boolean().default(true),
  created_at: z.string().optional(),
})

export type LLMResource = z.infer<typeof llmResourceSchema>
