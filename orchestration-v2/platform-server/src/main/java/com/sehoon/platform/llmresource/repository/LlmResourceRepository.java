package com.sehoon.platform.llmresource.repository;

import com.sehoon.platform.llmresource.domain.LlmResource;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface LlmResourceRepository extends JpaRepository<LlmResource, Long> {
    List<LlmResource> findByResourceTypeAndIsActiveOrderByPriorityDesc(String resourceType, boolean isActive);
    List<LlmResource> findByIsActiveOrderByPriorityDesc(boolean isActive);
}
