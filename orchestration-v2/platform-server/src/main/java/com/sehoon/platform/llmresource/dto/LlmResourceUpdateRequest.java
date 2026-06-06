package com.sehoon.platform.llmresource.dto;

import jakarta.validation.constraints.Min;

public record LlmResourceUpdateRequest(
        String name,
        String modelName,
        String apiBase,
        String apiKey,
        String deploymentName,
        String apiVersion,

        @Min(0)
        int priority,

        @Min(1)
        int weight
) {}
