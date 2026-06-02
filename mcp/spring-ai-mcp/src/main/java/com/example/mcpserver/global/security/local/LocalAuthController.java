package com.example.mcpserver.global.security.local;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * AUTH_MODE=local 전용 토큰 발급 엔드포인트.
 *
 * 요청: POST /auth/token
 *       { "username": "mcp-client", "password": "secret" }
 * 응답: { "access_token": "...", "token_type": "Bearer", "expires_in": 3600 }
 */
@Slf4j
@RestController
@RequiredArgsConstructor
public class LocalAuthController {

    private final LocalAuthProperties props;
    private final LocalJwtProvider jwtProvider;
    private final PasswordEncoder passwordEncoder;

    @PostMapping("/auth/token")
    public ResponseEntity<?> token(@RequestBody LoginRequest req) {
        LocalAuthProperties.UserConfig user = props.getUsers().stream()
                .filter(u -> u.username().equals(req.username()))
                .findFirst()
                .orElse(null);

        if (user == null || !passwordEncoder.matches(req.password(), user.password())) {
            log.warn("[LOCAL-AUTH] Login failed: username={}", req.username());
            return ResponseEntity.status(401)
                    .body(Map.of("error", "Invalid credentials"));
        }

        String token = jwtProvider.generateToken(user.username(), user.roles());
        log.info("[LOCAL-AUTH] Token issued: username={}, roles={}", user.username(), user.roles());

        return ResponseEntity.ok(Map.of(
                "access_token", token,
                "token_type", "Bearer",
                "expires_in", props.getJwtExpirationSeconds()
        ));
    }

    public record LoginRequest(String username, String password) {}
}
