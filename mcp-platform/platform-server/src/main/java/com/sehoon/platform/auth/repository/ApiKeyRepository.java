package com.sehoon.platform.auth.repository;

import com.sehoon.platform.auth.domain.ApiKey;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ApiKeyRepository extends JpaRepository<ApiKey, Long> {
    Optional<ApiKey> findByKey(String key);
    List<ApiKey> findByUserId(Long userId);
    List<ApiKey> findByUserIdAndIsActive(Long userId, boolean isActive);
    long countByIsActive(boolean isActive);
}
