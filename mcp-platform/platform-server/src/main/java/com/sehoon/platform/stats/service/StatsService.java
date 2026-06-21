package com.sehoon.platform.stats.service;

import com.sehoon.platform.auth.repository.ApiKeyRepository;
import com.sehoon.platform.stats.dto.StatsResponse;
import com.sehoon.platform.user.domain.UserStatus;
import com.sehoon.platform.user.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class StatsService {

    private final UserRepository userRepository;
    private final ApiKeyRepository apiKeyRepository;

    public StatsService(UserRepository userRepository, ApiKeyRepository apiKeyRepository) {
        this.userRepository = userRepository;
        this.apiKeyRepository = apiKeyRepository;
    }

    public StatsResponse getStats() {
        long totalUsers = userRepository.count();
        long activeUsers = userRepository.countByStatus(UserStatus.ACTIVE);
        long totalApiKeys = apiKeyRepository.count();
        long activeApiKeys = apiKeyRepository.countByIsActive(true);
        return new StatsResponse(totalUsers, activeUsers, totalApiKeys, activeApiKeys);
    }
}
