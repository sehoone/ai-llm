package com.sehoon.platform.user.dto;

import com.sehoon.platform.user.domain.UserRole;
import jakarta.validation.constraints.*;

public record AdminUserCreateRequest(
        @NotBlank(message = "사용자명은 필수입니다.")
        @Size(min = 2, max = 50)
        String username,

        @NotBlank(message = "이메일은 필수입니다.")
        @Email
        String email,

        @NotBlank(message = "비밀번호는 필수입니다.")
        @Size(min = 8, max = 64)
        String password,

        UserRole role
) {
    public AdminUserCreateRequest {
        if (role == null) role = UserRole.USER;
    }
}
