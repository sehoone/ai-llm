package com.llmonl.platform.auth.service;

import com.llmonl.platform.auth.domain.RefreshToken;
import com.llmonl.platform.auth.dto.LoginRequest;
import com.llmonl.platform.auth.dto.LoginResponse;
import com.llmonl.platform.auth.dto.RegisterRequest;
import com.llmonl.platform.auth.repository.RefreshTokenRepository;
import com.llmonl.platform.common.exception.BusinessException;
import com.llmonl.platform.common.exception.ErrorCode;
import com.llmonl.platform.common.security.JwtProvider;
import com.llmonl.platform.user.domain.User;
import com.llmonl.platform.user.dto.UserResponse;
import com.llmonl.platform.user.repository.UserRepository;
import org.springframework.beans.factory.annotation.Value;
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
    private final KeycloakAuthService keycloakAuthService;

    @Value("${auth.mode:jwt}")
    private String authMode;

    public AuthService(UserRepository userRepository,
                       RefreshTokenRepository refreshTokenRepository,
                       JwtProvider jwtProvider,
                       PasswordEncoder passwordEncoder,
                       KeycloakAuthService keycloakAuthService) {
        this.userRepository = userRepository;
        this.refreshTokenRepository = refreshTokenRepository;
        this.jwtProvider = jwtProvider;
        this.passwordEncoder = passwordEncoder;
        this.keycloakAuthService = keycloakAuthService;
    }

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

    public LoginResponse login(LoginRequest request) {
        if ("keycloak".equals(authMode)) {
            return keycloakAuthService.login(request);
        }
        return localLogin(request);
    }

    public LoginResponse refresh(String rawRefreshToken) {
        if ("keycloak".equals(authMode)) {
            return keycloakAuthService.refresh(rawRefreshToken);
        }
        return localRefresh(rawRefreshToken);
    }

    public void logout(String rawRefreshToken) {
        if (!"keycloak".equals(authMode)) {
            refreshTokenRepository.findByToken(rawRefreshToken)
                    .ifPresent(RefreshToken::revoke);
        }
        // Keycloak 모드에서는 클라이언트가 Keycloak logout endpoint를 직접 호출하거나
        // 토큰을 버리면 되므로 서버측 처리 불필요
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
