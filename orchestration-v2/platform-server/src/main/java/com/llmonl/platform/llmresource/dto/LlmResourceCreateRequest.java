package com.llmonl.platform.llmresource.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public record LlmResourceCreateRequest(
        @NotBlank(message = "리소스 이름은 필수입니다.")
        String name,

        @NotBlank(message = "resource_type은 필수입니다.")
        @Pattern(regexp = "chat|embedding", message = "resource_type은 'chat' 또는 'embedding'이어야 합니다.")
        String resourceType,

        String modelName,

        @NotBlank(message = "provider는 필수입니다.")
        String provider,

        @NotBlank(message = "api_base는 필수입니다.")
        String apiBase,

        @NotBlank(message = "api_key는 필수입니다.")
        String apiKey,

        String deploymentName,
        String apiVersion,
        String region,

        @Min(value = 0, message = "priority는 0 이상이어야 합니다.")
        int priority,

        @Min(value = 1, message = "weight는 1 이상이어야 합니다.")
        int weight
) {}
