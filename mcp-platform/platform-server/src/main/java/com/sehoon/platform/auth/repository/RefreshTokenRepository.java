package com.sehoon.platform.auth.repository;

import com.sehoon.platform.auth.domain.RefreshToken;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

import java.time.LocalDateTime;
import java.util.Optional;

public interface RefreshTokenRepository extends JpaRepository<RefreshToken, Long> {
    Optional<RefreshToken> findByToken(String token);

    @Modifying
    @Query("UPDATE RefreshToken r SET r.isRevoked = true WHERE r.userId = :userId")
    void revokeAllByUserId(Long userId);

    @Modifying
    @Query("DELETE FROM RefreshToken r WHERE r.expiresAt < :now OR r.isRevoked = true")
    void deleteExpiredAndRevoked(LocalDateTime now);
}
