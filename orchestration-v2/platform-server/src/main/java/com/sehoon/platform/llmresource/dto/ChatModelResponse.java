package com.sehoon.platform.llmresource.dto;

import com.sehoon.platform.llmresource.domain.LlmResource;

public record ChatModelResponse(Long id, String name, String modelName) {
    public static ChatModelResponse from(LlmResource r) {
        return new ChatModelResponse(r.getId(), r.getName(), r.getModelName());
    }
}
