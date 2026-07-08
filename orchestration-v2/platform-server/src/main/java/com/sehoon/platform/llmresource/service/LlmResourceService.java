package com.sehoon.platform.llmresource.service;

import com.sehoon.platform.common.audit.AuditAction;
import com.sehoon.platform.common.audit.Auditable;
import com.sehoon.platform.common.exception.BusinessException;
import com.sehoon.platform.common.exception.ErrorCode;
import com.sehoon.platform.llmresource.domain.LlmResource;
import com.sehoon.platform.llmresource.dto.ChatModelResponse;
import com.sehoon.platform.llmresource.dto.LlmResourceCreateRequest;
import com.sehoon.platform.llmresource.dto.LlmResourceResponse;
import com.sehoon.platform.llmresource.dto.LlmResourceUpdateRequest;
import com.sehoon.platform.llmresource.repository.LlmResourceRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@Transactional(readOnly = true)
public class LlmResourceService {

    private final LlmResourceRepository repository;

    public LlmResourceService(LlmResourceRepository repository) {
        this.repository = repository;
    }

    public List<ChatModelResponse> getChatModels() {
        return repository.findByResourceTypeAndIsActiveOrderByPriorityDesc("chat", true).stream()
                .map(ChatModelResponse::from)
                .toList();
    }

    public List<LlmResourceResponse> getAll() {
        return repository.findAllByOrderByPriorityDesc().stream()
                .map(LlmResourceResponse::from)
                .toList();
    }

    public List<LlmResourceResponse> getByType(String resourceType) {
        return repository.findByResourceTypeOrderByPriorityDesc(resourceType).stream()
                .map(LlmResourceResponse::from)
                .toList();
    }

    public LlmResourceResponse getById(Long id) {
        return LlmResourceResponse.from(find(id));
    }

    @Transactional
    @Auditable(action = AuditAction.LLM_RESOURCE_CREATE, resourceType = "LLM_RESOURCE")
    public LlmResourceResponse create(LlmResourceCreateRequest req) {
        LlmResource resource = new LlmResource(
                req.name(), req.resourceType(), req.modelName(),
                req.provider(), req.apiBase(), req.apiKey(),
                req.deploymentName(), req.apiVersion(), req.region(),
                req.priority(), req.weight()
        );
        return LlmResourceResponse.from(repository.save(resource));
    }

    @Transactional
    @Auditable(action = AuditAction.LLM_RESOURCE_UPDATE, resourceType = "LLM_RESOURCE",
               captureFirstArgAsResourceId = true)
    public LlmResourceResponse update(Long id, LlmResourceUpdateRequest req) {
        LlmResource resource = find(id);
        resource.update(req.name(), req.resourceType(), req.modelName(),
                req.provider(), req.apiBase(), req.apiKey(),
                req.deploymentName(), req.apiVersion(), req.region(),
                req.priority(), req.weight(), req.isActive());
        return LlmResourceResponse.from(resource);
    }

    @Transactional
    @Auditable(action = AuditAction.LLM_RESOURCE_TOGGLE, resourceType = "LLM_RESOURCE",
               captureFirstArgAsResourceId = true)
    public LlmResourceResponse toggleActive(Long id) {
        LlmResource resource = find(id);
        resource.toggleActive();
        return LlmResourceResponse.from(resource);
    }

    @Transactional
    @Auditable(action = AuditAction.LLM_RESOURCE_DELETE, resourceType = "LLM_RESOURCE",
               captureFirstArgAsResourceId = true)
    public void delete(Long id) {
        repository.delete(find(id));
    }

    private LlmResource find(Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.LLM_RESOURCE_NOT_FOUND));
    }
}
