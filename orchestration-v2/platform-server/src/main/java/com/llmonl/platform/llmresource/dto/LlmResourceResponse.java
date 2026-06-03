package com.llmonl.platform.llmresource.dto;

import com.llmonl.platform.llmresource.domain.LlmResource;

public record LlmResourceResponse(
        Long id,
        String name,
        String resourceType,
        String modelName,
        String provider,
        String apiBase,
        String deploymentName,
        String apiVersion,
        String region,
        int priority,
        int weight,
        boolean isActive
) {
    public static LlmResourceResponse from(LlmResource r) {
        return new LlmResourceResponse(
                r.getId(), r.getName(), r.getResourceType(), r.getModelName(),
                r.getProvider(), r.getApiBase(), r.getDeploymentName(),
                r.getApiVersion(), r.getRegion(), r.getPriority(), r.getWeight(), r.isActive()
        );
    }
}
