package com.multicampus.llmbackend.domain.health;

import com.multicampus.llmbackend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Health", description = "헬스체크 API")
@RestController
public class HealthController {

    @Operation(summary = "헬스체크", description = "서버 상태를 확인합니다.")
    @GetMapping("/health")
    public ApiResponse<String> health() {
        return ApiResponse.success("OK");
    }
}
