package com.llmonl.platform.llmresource.api;

import com.llmonl.platform.common.dto.ApiResponse;
import com.llmonl.platform.llmresource.dto.ChatModelResponse;
import com.llmonl.platform.llmresource.dto.LlmResourceCreateRequest;
import com.llmonl.platform.llmresource.dto.LlmResourceResponse;
import com.llmonl.platform.llmresource.dto.LlmResourceUpdateRequest;
import com.llmonl.platform.llmresource.service.LlmResourceService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/llm-resources")
@Tag(name = "LLM Resources", description = "LLM 모델 리소스 설정 (ADMIN 이상)")
public class LlmResourceController {

    private final LlmResourceService service;

    public LlmResourceController(LlmResourceService service) {
        this.service = service;
    }

    @GetMapping("/chat-models")
    @Operation(summary = "채팅용 LLM 모델 목록 (에이전트 모델 선택용, 인증 필요)")
    public ResponseEntity<ApiResponse<List<ChatModelResponse>>> getChatModels() {
        return ResponseEntity.ok(ApiResponse.ok(service.getChatModels()));
    }

    @GetMapping
    @Operation(summary = "활성 LLM 리소스 전체 조회")
    public ResponseEntity<ApiResponse<List<LlmResourceResponse>>> getAll(
            @RequestParam(required = false) String type) {
        List<LlmResourceResponse> result = type != null ? service.getByType(type) : service.getAll();
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @GetMapping("/{id}")
    @Operation(summary = "LLM 리소스 단건 조회")
    public ResponseEntity<ApiResponse<LlmResourceResponse>> getById(@PathVariable Long id) {
        return ResponseEntity.ok(ApiResponse.ok(service.getById(id)));
    }

    @PostMapping
    @Operation(summary = "LLM 리소스 등록")
    public ResponseEntity<ApiResponse<LlmResourceResponse>> create(
            @Valid @RequestBody LlmResourceCreateRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(service.create(request)));
    }

    @PatchMapping("/{id}")
    @Operation(summary = "LLM 리소스 수정")
    public ResponseEntity<ApiResponse<LlmResourceResponse>> update(
            @PathVariable Long id,
            @Valid @RequestBody LlmResourceUpdateRequest request) {
        return ResponseEntity.ok(ApiResponse.ok(service.update(id, request)));
    }

    @PatchMapping("/{id}/toggle")
    @Operation(summary = "LLM 리소스 활성/비활성 토글")
    public ResponseEntity<ApiResponse<LlmResourceResponse>> toggle(@PathVariable Long id) {
        return ResponseEntity.ok(ApiResponse.ok(service.toggleActive(id)));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "LLM 리소스 삭제")
    public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long id) {
        service.delete(id);
        return ResponseEntity.ok(ApiResponse.ok("LLM 리소스가 삭제되었습니다.", null));
    }
}
