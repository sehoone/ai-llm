package com.llmonl.platform.llmresource.dto;

import com.llmonl.platform.llmresource.domain.LlmResource;

public record ChatModelResponse(Long id, String name, String modelName) {
    public static ChatModelResponse from(LlmResource r) {
        return new ChatModelResponse(r.getId(), r.getName(), r.getModelName());
    }
}
