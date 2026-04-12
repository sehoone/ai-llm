package com.multicampus.llmbackend.domain.user.controller;

import com.multicampus.llmbackend.domain.user.dto.LoginRequest;
import com.multicampus.llmbackend.domain.user.dto.LoginResponse;
import com.multicampus.llmbackend.domain.user.dto.SignUpRequest;
import com.multicampus.llmbackend.domain.user.dto.SignUpResponse;
import com.multicampus.llmbackend.domain.user.service.UserService;
import com.multicampus.llmbackend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@Tag(name = "Auth", description = "인증 API")
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @Operation(summary = "회원가입", description = "이메일, 비밀번호, 이름으로 회원가입합니다.")
    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<SignUpResponse> signUp(@Valid @RequestBody SignUpRequest request) {
        return ApiResponse.success(userService.signUp(request));
    }

    @Operation(summary = "로그인", description = "이메일/비밀번호로 로그인 후 Access/Refresh Token을 반환합니다.")
    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return ApiResponse.success(userService.login(request));
    }
}
