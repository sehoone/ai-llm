package com.example.mcpserver.sample.tool;

import com.example.mcpserver.sample.db.entity.SampleItem;
import com.example.mcpserver.sample.db.mapper.SampleItemMapper;
import com.example.mcpserver.sample.db.repository.SampleItemRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * PostgreSQL 조회 샘플 — MyBatis(XML 매퍼)와 JPA(Spring Data)를 비교 제공.
 *
 * MyBatis:  XML에 SQL을 직접 작성 → 복잡한 쿼리, 동적 SQL에 유리
 * JPA:      메서드 이름 기반 쿼리 자동 생성 → 단순 CRUD, 타입 안전성에 유리
 *
 * 대상 테이블: sample_item (id, name, description, price)
 * DDL 참고:   src/main/resources/db/migration/V1__init_schema.sql
 */
@Component
@RequiredArgsConstructor
public class SampleDbTool {

    private static final int DEFAULT_LIMIT = 100;
    private static final int MAX_LIMIT = 500;

    private final SampleItemMapper sampleItemMapper;         // MyBatis
    private final SampleItemRepository sampleItemRepository; // JPA

    // ── MyBatis ───────────────────────────────────────────────────────────────

    @Tool(description = "[MyBatis] Retrieves items from sample_item table with pagination")
    public List<SampleItem> myBatisFindAllItems(
            @ToolParam(description = "Maximum number of items to return (1–500, default 100)") Integer limit,
            @ToolParam(description = "Number of items to skip for pagination (default 0)") Integer offset
    ) {
        int safeLimit = resolveLimit(limit);
        int safeOffset = offset != null && offset >= 0 ? offset : 0;
        return sampleItemMapper.findAll(safeLimit, safeOffset);
    }

    @Tool(description = "[MyBatis] Finds a sample item by its ID using MyBatis XML mapper")
    public SampleItem myBatisFindItemById(
            @ToolParam(description = "ID of the item to retrieve") Long id
    ) {
        if (id == null || id <= 0) {
            throw new IllegalArgumentException("id must be a positive number");
        }
        SampleItem item = sampleItemMapper.findById(id);
        if (item == null) {
            throw new RuntimeException("Item not found with id=" + id);
        }
        return item;
    }

    @Tool(description = "[MyBatis] Finds items whose name contains the given keyword (case-insensitive, PostgreSQL ILIKE)")
    public List<SampleItem> myBatisFindItemsByName(
            @ToolParam(description = "Keyword to search in item name") String name,
            @ToolParam(description = "Maximum number of items to return (1–500, default 100)") Integer limit
    ) {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("name must not be blank");
        }
        int safeLimit = resolveLimit(limit);
        return sampleItemMapper.findByName(name, safeLimit);
    }

    // ── JPA (Spring Data) ─────────────────────────────────────────────────────

    @Tool(description = "[JPA] Retrieves items from sample_item table using Spring Data JPA with pagination")
    public List<SampleItem> jpaFindAllItems(
            @ToolParam(description = "Maximum number of items to return (1–500, default 100)") Integer limit,
            @ToolParam(description = "Page number starting from 0 (default 0)") Integer page
    ) {
        int safeLimit = resolveLimit(limit);
        int safePage = page != null && page >= 0 ? page : 0;
        return sampleItemRepository.findAll(PageRequest.of(safePage, safeLimit)).getContent();
    }

    @Tool(description = "[JPA] Finds a sample item by its ID using Spring Data JPA")
    public SampleItem jpaFindItemById(
            @ToolParam(description = "ID of the item to retrieve") Long id
    ) {
        if (id == null || id <= 0) {
            throw new IllegalArgumentException("id must be a positive number");
        }
        return sampleItemRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Item not found with id=" + id));
    }

    @Tool(description = "[JPA] Finds items whose name contains the given keyword using Spring Data JPA (case-insensitive)")
    public List<SampleItem> jpaFindItemsByName(
            @ToolParam(description = "Keyword to search in item name") String name,
            @ToolParam(description = "Maximum number of items to return (1–500, default 100)") Integer limit
    ) {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("name must not be blank");
        }
        int safeLimit = resolveLimit(limit);
        return sampleItemRepository.findByNameContainingIgnoreCase(name, PageRequest.of(0, safeLimit));
    }

    private int resolveLimit(Integer requested) {
        if (requested == null || requested <= 0) return DEFAULT_LIMIT;
        return Math.min(requested, MAX_LIMIT);
    }
}
