package com.sehoon.platform.auth.service;

import com.sehoon.platform.auth.domain.ApiKey;
import com.sehoon.platform.auth.dto.ApiKeyCreateRequest;
import com.sehoon.platform.auth.dto.ApiKeyResponse;
import com.sehoon.platform.auth.dto.ApiKeyValidateResponse;
import com.sehoon.platform.auth.repository.ApiKeyRepository;
import com.sehoon.platform.common.exception.BusinessException;
import com.sehoon.platform.common.exception.ErrorCode;
import com.sehoon.platform.user.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.List;
import java.util.Optional;

@Service
@Transactional(readOnly = true)
public class ApiKeyService {

    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    private final ApiKeyRepository apiKeyRepository;
    private final UserRepository userRepository;

    public ApiKeyService(ApiKeyRepository apiKeyRepository, UserRepository userRepository) {
        this.apiKeyRepository = apiKeyRepository;
        this.userRepository = userRepository;
    }

    public List<ApiKeyResponse> getApiKeys(Long userId) {
        return apiKeyRepository.findByUserIdAndIsActive(userId, true).stream()
                .map(ApiKeyResponse::masked)
                .toList();
    }

    @Transactional
    public ApiKeyResponse createApiKey(Long userId, ApiKeyCreateRequest request) {
        String rawKey = generateKey();
        ApiKey apiKey = new ApiKey(userId, rawKey, request.name(), request.expiresAt());
        return ApiKeyResponse.from(apiKeyRepository.save(apiKey));
    }

    @Transactional
    public void revokeApiKey(Long userId, Long keyId) {
        ApiKey apiKey = apiKeyRepository.findById(keyId)
                .orElseThrow(() -> new BusinessException(ErrorCode.API_KEY_NOT_FOUND));

        if (!apiKey.getUserId().equals(userId)) {
            throw new BusinessException(ErrorCode.FORBIDDEN);
        }

        apiKey.deactivate();
    }

    public Optional<ApiKeyValidateResponse> validateKey(String key) {
        return apiKeyRepository.findByKey(key)
                .filter(ApiKey::isActive)
                .filter(k -> !k.isExpired())
                .flatMap(k -> userRepository.findById(k.getUserId())
                        .filter(u -> u.isActive())
                        .map(u -> new ApiKeyValidateResponse(k.getId(), u.getId(), u.getUsername(), u.getRole().name())));
    }

    private String generateKey() {
        byte[] bytes = new byte[32];
        SECURE_RANDOM.nextBytes(bytes);
        return "sk-" + Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}
