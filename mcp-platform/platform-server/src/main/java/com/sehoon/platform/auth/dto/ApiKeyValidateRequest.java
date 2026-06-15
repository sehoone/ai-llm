package com.sehoon.platform.auth.dto;

import jakarta.validation.constraints.NotBlank;

public record ApiKeyValidateRequest(
        @NotBlank String key
) {}
