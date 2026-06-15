package com.sehoon.platform.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;

public record ApiKeyCreateRequest(
        @NotBlank(message = "API 키 이름은 필수입니다.")
        @Size(max = 100, message = "API 키 이름은 100자를 초과할 수 없습니다.")
        String name,

        LocalDateTime expiresAt
) {}
