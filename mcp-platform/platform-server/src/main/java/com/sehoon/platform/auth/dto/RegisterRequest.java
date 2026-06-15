package com.sehoon.platform.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record RegisterRequest(
        @NotBlank(message = "사용자명은 필수입니다.")
        @Size(min = 2, max = 50, message = "사용자명은 2~50자여야 합니다.")
        String username,

        @NotBlank(message = "이메일은 필수입니다.")
        @Email(message = "올바른 이메일 형식이 아닙니다.")
        String email,

        @NotBlank(message = "비밀번호는 필수입니다.")
        @Size(min = 8, max = 64, message = "비밀번호는 8~64자여야 합니다.")
        @Pattern(
                regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).+$",
                message = "비밀번호는 대소문자, 숫자, 특수문자를 각각 1개 이상 포함해야 합니다."
        )
        String password
) {}
