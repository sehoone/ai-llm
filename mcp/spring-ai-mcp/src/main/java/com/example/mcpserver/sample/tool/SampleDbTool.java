package com.example.mcpserver.sample.tool;

import com.example.mcpserver.sample.db.entity.SampleItem;
import com.example.mcpserver.sample.db.mapper.SampleItemMapper;
import com.example.mcpserver.sample.db.repository.SampleItemRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * PostgreSQL 조회 샘플 — MyBatis(XML 매퍼)와 JPA(Spring Data)를 비교 제공.
 *
 * MyBatis:  XML에 SQL을 직접 작성 → 복잡한 쿼리, 동적 SQL에 유리
 * JPA:      메서드 이름 기반 쿼리 자동 생성 → 단순 CRUD, 타입 안전성에 유리
 *
 * 대상 테이블: sample_item (id, name, description, price)
 * DDL 참고:   src/main/resources/sql/sample_schema.sql
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SampleDbTool {

    private final SampleItemMapper sampleItemMapper;         // MyBatis
    private final SampleItemRepository sampleItemRepository; // JPA

    // ── MyBatis ───────────────────────────────────────────────────────────────

    @Tool(description = "[MyBatis] Retrieves all items from the sample_item table")
    public List<SampleItem> myBatisFindAllItems() {
        log.info("myBatisFindAllItems called");
        return sampleItemMapper.findAll();
    }

    @Tool(description = "[MyBatis] Finds a sample item by its ID using MyBatis XML mapper")
    public SampleItem myBatisFindItemById(
            @ToolParam(description = "ID of the item to retrieve") Long id
    ) {
        if (id == null || id <= 0) {
            throw new IllegalArgumentException("id must be a positive number");
        }
        log.info("myBatisFindItemById called: id={}", id);
        SampleItem item = sampleItemMapper.findById(id);
        if (item == null) {
            throw new RuntimeException("Item not found with id=" + id);
        }
        return item;
    }

    @Tool(description = "[MyBatis] Finds items whose name contains the given keyword (case-insensitive, PostgreSQL ILIKE)")
    public List<SampleItem> myBatisFindItemsByName(
            @ToolParam(description = "Keyword to search in item name") String name
    ) {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("name must not be blank");
        }
        log.info("myBatisFindItemsByName called");
        return sampleItemMapper.findByName(name);
    }

    // ── JPA (Spring Data) ─────────────────────────────────────────────────────

    @Tool(description = "[JPA] Retrieves all items from the sample_item table using Spring Data JPA")
    public List<SampleItem> jpaFindAllItems() {
        log.info("jpaFindAllItems called");
        return sampleItemRepository.findAll();
    }

    @Tool(description = "[JPA] Finds a sample item by its ID using Spring Data JPA")
    public SampleItem jpaFindItemById(
            @ToolParam(description = "ID of the item to retrieve") Long id
    ) {
        if (id == null || id <= 0) {
            throw new IllegalArgumentException("id must be a positive number");
        }
        log.info("jpaFindItemById called: id={}", id);
        return sampleItemRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Item not found with id=" + id));
    }

    @Tool(description = "[JPA] Finds items whose name contains the given keyword using Spring Data JPA (case-insensitive)")
    public List<SampleItem> jpaFindItemsByName(
            @ToolParam(description = "Keyword to search in item name") String name
    ) {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("name must not be blank");
        }
        log.info("jpaFindItemsByName called");
        return sampleItemRepository.findByNameContainingIgnoreCase(name);
    }
}
