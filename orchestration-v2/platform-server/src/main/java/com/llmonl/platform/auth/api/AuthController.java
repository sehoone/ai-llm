package com.llmonl.platform.auth.api;

import com.llmonl.platform.auth.dto.LoginRequest;
import com.llmonl.platform.auth.dto.LoginResponse;
import com.llmonl.platform.auth.dto.RegisterRequest;
import com.llmonl.platform.auth.dto.TokenRefreshRequest;
import com.llmonl.platform.auth.service.AuthService;
import com.llmonl.platform.common.dto.ApiResponse;
import com.llmonl.platform.user.dto.UserResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/auth")
@Tag(name = "Auth", description = "인증 API")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/register")
    @Operation(summary = "회원가입")
    public ResponseEntity<ApiResponse<UserResponse>> register(@Valid @RequestBody RegisterRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok("회원가입이 완료되었습니다.", authService.register(request)));
    }

    @PostMapping("/login")
    @Operation(summary = "로그인 — access/refresh 토큰 발급")
    public ResponseEntity<ApiResponse<LoginResponse>> login(@Valid @RequestBody LoginRequest request) {
        return ResponseEntity.ok(ApiResponse.ok(authService.login(request)));
    }

    @PostMapping("/refresh")
    @Operation(summary = "토큰 갱신")
    public ResponseEntity<ApiResponse<LoginResponse>> refresh(@Valid @RequestBody TokenRefreshRequest request) {
        return ResponseEntity.ok(ApiResponse.ok(authService.refresh(request.refreshToken())));
    }

    @PostMapping("/logout")
    @Operation(summary = "로그아웃 — refresh 토큰 폐기")
    public ResponseEntity<ApiResponse<Void>> logout(@Valid @RequestBody TokenRefreshRequest request) {
        authService.logout(request.refreshToken());
        return ResponseEntity.ok(ApiResponse.ok("로그아웃되었습니다.", null));
    }
}
