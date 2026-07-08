package com.sehoon.platform.llmresource.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;

public record LlmResourceUpdateRequest(
        String name,

        @Pattern(regexp = "chat|embedding", message = "resource_type은 'chat' 또는 'embedding'이어야 합니다.")
        String resourceType,

        String modelName,
        String provider,
        String apiBase,
        String apiKey,
        String deploymentName,
        String apiVersion,
        String region,

        @Min(0)
        Integer priority,

        @Min(1)
        Integer weight,

        Boolean isActive
) {}
