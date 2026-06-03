package com.llmonl.platform.llmresource.service;

import com.llmonl.platform.common.exception.BusinessException;
import com.llmonl.platform.common.exception.ErrorCode;
import com.llmonl.platform.llmresource.domain.LlmResource;
import com.llmonl.platform.llmresource.dto.ChatModelResponse;
import com.llmonl.platform.llmresource.dto.LlmResourceCreateRequest;
import com.llmonl.platform.llmresource.dto.LlmResourceResponse;
import com.llmonl.platform.llmresource.dto.LlmResourceUpdateRequest;
import com.llmonl.platform.llmresource.repository.LlmResourceRepository;
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
        return repository.findByIsActiveOrderByPriorityDesc(true).stream()
                .map(LlmResourceResponse::from)
                .toList();
    }

    public List<LlmResourceResponse> getByType(String resourceType) {
        return repository.findByResourceTypeAndIsActiveOrderByPriorityDesc(resourceType, true).stream()
                .map(LlmResourceResponse::from)
                .toList();
    }

    public LlmResourceResponse getById(Long id) {
        return LlmResourceResponse.from(find(id));
    }

    @Transactional
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
    public LlmResourceResponse update(Long id, LlmResourceUpdateRequest req) {
        LlmResource resource = find(id);
        resource.update(req.name(), req.modelName(), req.apiBase(), req.apiKey(),
                req.deploymentName(), req.apiVersion(), req.priority(), req.weight());
        return LlmResourceResponse.from(resource);
    }

    @Transactional
    public LlmResourceResponse toggleActive(Long id) {
        LlmResource resource = find(id);
        resource.toggleActive();
        return LlmResourceResponse.from(resource);
    }

    @Transactional
    public void delete(Long id) {
        repository.delete(find(id));
    }

    private LlmResource find(Long id) {
        return repository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.LLM_RESOURCE_NOT_FOUND));
    }
}
