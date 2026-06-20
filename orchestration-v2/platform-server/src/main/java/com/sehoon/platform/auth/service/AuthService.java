package com.sehoon.platform.auth.service;

import com.sehoon.platform.auth.domain.RefreshToken;
import com.sehoon.platform.auth.dto.LoginRequest;
import com.sehoon.platform.auth.dto.LoginResponse;
import com.sehoon.platform.auth.dto.RegisterRequest;
import com.sehoon.platform.auth.repository.RefreshTokenRepository;
import com.sehoon.platform.common.audit.AuditAction;
import com.sehoon.platform.common.audit.Auditable;
import com.sehoon.platform.common.exception.BusinessException;
import com.sehoon.platform.common.exception.ErrorCode;
import com.sehoon.platform.common.security.JwtProvider;
import com.sehoon.platform.user.domain.User;
import com.sehoon.platform.user.dto.UserResponse;
import com.sehoon.platform.user.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Service
@Transactional
public class AuthService {

    private final UserRepository userRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final JwtProvider jwtProvider;
    private final PasswordEncoder passwordEncoder;

    public AuthService(UserRepository userRepository,
                       RefreshTokenRepository refreshTokenRepository,
                       JwtProvider jwtProvider,
                       PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.refreshTokenRepository = refreshTokenRepository;
        this.jwtProvider = jwtProvider;
        this.passwordEncoder = passwordEncoder;
    }

    @Auditable(action = AuditAction.AUTH_REGISTER, resourceType = "USER")
    public UserResponse register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new BusinessException(ErrorCode.EMAIL_ALREADY_EXISTS);
        }
        if (userRepository.existsByUsername(request.username())) {
            throw new BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS);
        }

        User user = new User(
                request.username(),
                request.email(),
                passwordEncoder.encode(request.password())
        );
        return UserResponse.from(userRepository.save(user));
    }

    // 로그인 성공·실패 모두 AOP가 캡처 (REQUIRES_NEW 트랜잭션으로 저장되므로 롤백 무관)
    @Auditable(action = AuditAction.AUTH_LOGIN_SUCCESS, resourceType = "AUTH")
    public LoginResponse login(LoginRequest request) {
        return localLogin(request);
    }

    @Auditable(action = AuditAction.AUTH_TOKEN_REFRESH, resourceType = "AUTH")
    public LoginResponse refresh(String rawRefreshToken) {
        return localRefresh(rawRefreshToken);
    }

    @Auditable(action = AuditAction.AUTH_LOGOUT, resourceType = "AUTH")
    public void logout(String rawRefreshToken) {
        refreshTokenRepository.findByToken(rawRefreshToken)
                .ifPresent(RefreshToken::revoke);
    }

    private LoginResponse localLogin(LoginRequest request) {
        User user = userRepository.findByEmail(request.email())
                .orElseThrow(() -> new BusinessException(ErrorCode.INVALID_CREDENTIALS));

        if (!passwordEncoder.matches(request.password(), user.getHashedPassword())) {
            throw new BusinessException(ErrorCode.INVALID_CREDENTIALS);
        }

        if (!user.isActive()) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "비활성화된 계정입니다.");
        }

        return issueTokens(user);
    }

    private LoginResponse localRefresh(String rawRefreshToken) {
        RefreshToken stored = refreshTokenRepository.findByToken(rawRefreshToken)
                .orElseThrow(() -> new BusinessException(ErrorCode.TOKEN_INVALID));

        if (!stored.isValid()) {
            throw new BusinessException(ErrorCode.TOKEN_EXPIRED);
        }

        stored.revoke();

        User user = userRepository.findById(stored.getUserId())
                .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));

        return issueTokens(user);
    }

    private LoginResponse issueTokens(User user) {
        String accessToken = jwtProvider.createAccessToken(
                user.getId(), user.getUsername(), user.getEmail(), user.getRole().name());

        String rawRefreshToken = jwtProvider.createRefreshToken(user.getId());

        LocalDateTime refreshExpiry = LocalDateTime.now()
                .plusMinutes(jwtProvider.getRefreshTokenExpireMinutes());

        refreshTokenRepository.save(new RefreshToken(user.getId(), rawRefreshToken, refreshExpiry));

        long expiresIn = jwtProvider.getAccessTokenExpireMinutes() * 60;
        return new LoginResponse(accessToken, rawRefreshToken, expiresIn, UserResponse.from(user));
    }
}
