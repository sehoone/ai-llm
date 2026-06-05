package com.sehoon.platform.user.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Size;

public record UserUpdateRequest(
        @Size(min = 2, max = 50, message = "사용자명은 2~50자여야 합니다.")
        String username,

        @Email(message = "올바른 이메일 형식이 아닙니다.")
        String email
) {}
