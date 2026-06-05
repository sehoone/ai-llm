package com.sehoon.platform.auth.service;

import java.io.IOException;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sehoon.platform.auth.dto.LoginRequest;
import com.sehoon.platform.auth.dto.LoginResponse;
import com.sehoon.platform.common.config.KeycloakProperties;
import com.sehoon.platform.common.exception.BusinessException;
import com.sehoon.platform.common.exception.ErrorCode;
import com.sehoon.platform.user.domain.User;
import com.sehoon.platform.user.domain.UserRole;
import com.sehoon.platform.user.dto.UserResponse;
import com.sehoon.platform.user.repository.UserRepository;

/**
 * Keycloak Direct Access Grant를 통해 로그인/갱신을 처리하고,
 * 로컬 users 테이블과 Keycloak 사용자를 JIT 프로비저닝한다.
 *
 * AUTH_MODE=keycloak 환경에서 AuthController에서 호출된다.
 */
@Service
@Transactional
public class KeycloakAuthService {

    private static final Logger log = LoggerFactory.getLogger(KeycloakAuthService.class);

    private final KeycloakProperties keycloakProperties;
    private final UserRepository userRepository;
    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    public KeycloakAuthService(KeycloakProperties keycloakProperties,
                               UserRepository userRepository) {
        this.keycloakProperties = keycloakProperties;
        this.userRepository = userRepository;
    }

    /**
     * Keycloak Password Grant로 로그인한다.
     *
     * @param request 이메일 + 비밀번호
     * @return Keycloak access/refresh 토큰과 사용자 정보
     */
    public LoginResponse login(LoginRequest request) {
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", "password");
        form.add("client_id", keycloakProperties.getClientId());
        form.add("client_secret", keycloakProperties.getClientSecret());
        form.add("username", request.email());
        form.add("password", request.password());

        Map<String, Object> tokens = callTokenEndpoint(form);
        return buildLoginResponse(tokens);
    }

    /**
     * Keycloak refresh_token으로 새 토큰을 발급한다.
     *
     * @param refreshToken 기존 refresh 토큰
     * @return 갱신된 access/refresh 토큰과 사용자 정보
     */
    public LoginResponse refresh(String refreshToken) {
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", "refresh_token");
        form.add("client_id", keycloakProperties.getClientId());
        form.add("client_secret", keycloakProperties.getClientSecret());
        form.add("refresh_token", refreshToken);

        Map<String, Object> tokens = callTokenEndpoint(form);
        return buildLoginResponse(tokens);
    }

    private LoginResponse buildLoginResponse(Map<String, Object> tokens) {
        String accessToken = (String) tokens.get("access_token");
        String newRefreshToken = (String) tokens.get("refresh_token");
        long expiresIn = ((Number) tokens.getOrDefault("expires_in", 600)).longValue();

        Map<String, Object> claims = decodeJwtPayload(accessToken);
        User user = provisionUser(claims);

        return new LoginResponse(accessToken, newRefreshToken, expiresIn, UserResponse.from(user));
    }

    private Map<String, Object> callTokenEndpoint(MultiValueMap<String, String> form) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);
        HttpEntity<MultiValueMap<String, String>> entity = new HttpEntity<>(form, headers);

        try {
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                    keycloakProperties.getTokenEndpoint(), HttpMethod.POST, entity,
                    new ParameterizedTypeReference<Map<String, Object>>() {});
            return response.getBody();
        } catch (HttpClientErrorException.Unauthorized | HttpClientErrorException.BadRequest e) {
            log.warn("keycloak_login_failed status={}", e.getStatusCode());
            throw new BusinessException(ErrorCode.INVALID_CREDENTIALS);
        } catch (RestClientException e) {
            log.error("keycloak_token_endpoint_error", e);
            throw new BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, "Keycloak 인증 서버에 연결할 수 없습니다.");
        }
    }

    /**
     * JWT payload를 Base64URL 디코딩하여 클레임 맵으로 반환한다.
     * 서명 검증은 하지 않는다 (신뢰된 Keycloak 서버에서 직접 받은 토큰이므로).
     */
    private Map<String, Object> decodeJwtPayload(String token) {
        try {
            String[] parts = token.split("\\.");
            byte[] decoded = Base64.getUrlDecoder().decode(parts[1]);
            return objectMapper.readValue(decoded, new TypeReference<Map<String, Object>>() {});
        } catch (IOException e) {
            log.error("keycloak_token_decode_error", e);
            throw new BusinessException(ErrorCode.TOKEN_INVALID, "Keycloak 토큰 파싱 실패");
        }
    }

    /**
     * Keycloak 클레임에서 사용자를 로컬 DB에 조회하거나 JIT 생성한다.
     */
    @SuppressWarnings("unchecked")
    private User provisionUser(Map<String, Object> claims) {
        String keycloakId = (String) claims.get("sub");
        String email = (String) claims.get("email");
        String preferredUsername = (String) claims.get("preferred_username");

        Map<String, Object> realmAccess = (Map<String, Object>) claims.get("realm_access");
        List<String> roles = realmAccess != null
                ? (List<String>) realmAccess.get("roles")
                : List.of();
        UserRole role = mapRole(roles);

        return userRepository.findByKeycloakId(keycloakId).orElseGet(() -> {
            // 이메일로 기존 사용자 조회
            Optional<User> byEmail = email != null ? userRepository.findByEmail(email) : Optional.empty();
            if (byEmail.isPresent()) {
                User existing = byEmail.get();
                existing.setKeycloakId(keycloakId);
                log.info("keycloak_id_linked_by_email userId={} keycloakId={}", existing.getId(), keycloakId);
                return userRepository.save(existing);
            }
            // username으로 기존 사용자 조회 (이메일 불일치 시 fallback)
            String username = (preferredUsername != null && !preferredUsername.isBlank())
                    ? preferredUsername
                    : (email != null ? email.split("@")[0] : keycloakId);
            Optional<User> byUsername = userRepository.findByUsername(username);
            if (byUsername.isPresent()) {
                User existing = byUsername.get();
                existing.setKeycloakId(keycloakId);
                log.info("keycloak_id_linked_by_username userId={} keycloakId={}", existing.getId(), keycloakId);
                return userRepository.save(existing);
            }
            // 신규 사용자 생성
            User newUser = new User(username, email != null ? email : "", "");
            newUser.setKeycloakId(keycloakId);
            newUser.changeRole(role);
            log.info("keycloak_user_provisioned keycloakId={} email={}", keycloakId, email);
            return userRepository.save(newUser);
        });
    }

    private UserRole mapRole(List<String> roles) {
        if (roles == null) return UserRole.USER;
        if (roles.contains("superadmin")) return UserRole.SUPERADMIN;
        if (roles.contains("admin")) return UserRole.ADMIN;
        return UserRole.USER;
    }
}
