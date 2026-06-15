package com.sehoon.platform.auth.api;

import com.sehoon.platform.auth.dto.ApiKeyCreateRequest;
import com.sehoon.platform.auth.dto.ApiKeyResponse;
import com.sehoon.platform.auth.dto.ApiKeyValidateRequest;
import com.sehoon.platform.auth.dto.ApiKeyValidateResponse;
import com.sehoon.platform.auth.service.ApiKeyService;
import com.sehoon.platform.common.dto.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/api-keys")
@Tag(name = "API Keys", description = "API 키 관리")
public class ApiKeyController {

    private final ApiKeyService apiKeyService;

    public ApiKeyController(ApiKeyService apiKeyService) {
        this.apiKeyService = apiKeyService;
    }

    @GetMapping
    @Operation(summary = "내 API 키 목록 조회")
    public ResponseEntity<ApiResponse<List<ApiKeyResponse>>> getApiKeys(@AuthenticationPrincipal String userId) {
        return ResponseEntity.ok(ApiResponse.ok(apiKeyService.getApiKeys(Long.parseLong(userId))));
    }

    @PostMapping
    @Operation(summary = "API 키 생성 (전체 키는 생성 시 1회만 노출)")
    public ResponseEntity<ApiResponse<ApiKeyResponse>> createApiKey(
            @AuthenticationPrincipal String userId,
            @Valid @RequestBody ApiKeyCreateRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(apiKeyService.createApiKey(Long.parseLong(userId), request)));
    }

    @DeleteMapping("/{keyId}")
    @Operation(summary = "API 키 폐기")
    public ResponseEntity<ApiResponse<Void>> revokeApiKey(
            @AuthenticationPrincipal String userId,
            @PathVariable Long keyId) {
        apiKeyService.revokeApiKey(Long.parseLong(userId), keyId);
        return ResponseEntity.ok(ApiResponse.ok("API 키가 폐기되었습니다.", null));
    }

    @PostMapping("/validate")
    @Operation(summary = "API 키 유효성 검증 (서비스 간 내부 호출용)")
    public ResponseEntity<ApiResponse<ApiKeyValidateResponse>> validateApiKey(
            @Valid @RequestBody ApiKeyValidateRequest request) {
        return apiKeyService.validateKey(request.key())
                .map(r -> ResponseEntity.ok(ApiResponse.ok(r)))
                .orElse(ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                        .body(ApiResponse.fail("유효하지 않거나 만료된 API 키입니다.")));
    }
}
