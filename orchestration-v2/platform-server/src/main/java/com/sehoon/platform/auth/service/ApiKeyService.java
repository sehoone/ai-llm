package com.sehoon.platform.auth.service;

import com.sehoon.platform.auth.domain.ApiKey;
import com.sehoon.platform.auth.dto.ApiKeyCreateRequest;
import com.sehoon.platform.auth.dto.ApiKeyResponse;
import com.sehoon.platform.auth.repository.ApiKeyRepository;
import com.sehoon.platform.common.audit.AuditAction;
import com.sehoon.platform.common.audit.Auditable;
import com.sehoon.platform.common.exception.BusinessException;
import com.sehoon.platform.common.exception.ErrorCode;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.List;

@Service
@Transactional(readOnly = true)
public class ApiKeyService {

    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    private final ApiKeyRepository apiKeyRepository;

    public ApiKeyService(ApiKeyRepository apiKeyRepository) {
        this.apiKeyRepository = apiKeyRepository;
    }

    public List<ApiKeyResponse> getApiKeys(Long userId) {
        return apiKeyRepository.findByUserId(userId).stream()
                .map(ApiKeyResponse::masked)
                .toList();
    }

    @Transactional
    @Auditable(action = AuditAction.API_KEY_CREATE, resourceType = "API_KEY")
    public ApiKeyResponse createApiKey(Long userId, ApiKeyCreateRequest request) {
        String rawKey = generateKey();
        ApiKey apiKey = new ApiKey(userId, rawKey, request.name(), request.expiresAt());
        return ApiKeyResponse.from(apiKeyRepository.save(apiKey));
    }

    @Transactional
    @Auditable(action = AuditAction.API_KEY_REVOKE, resourceType = "API_KEY",
               captureFirstArgAsResourceId = true)
    public void revokeApiKey(Long userId, Long keyId) {
        ApiKey apiKey = apiKeyRepository.findById(keyId)
                .orElseThrow(() -> new BusinessException(ErrorCode.API_KEY_NOT_FOUND));

        if (!apiKey.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.FORBIDDEN);
        }

        apiKey.deactivate();
    }

    private String generateKey() {
        byte[] bytes = new byte[32];
        SECURE_RANDOM.nextBytes(bytes);
        return "sk-" + Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}
