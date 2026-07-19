package com.poc.vectorsearch.controller;

import com.poc.vectorsearch.dto.BulkEmbeddingItem;
import com.poc.vectorsearch.dto.BulkEmbeddingResponse;
import com.poc.vectorsearch.dto.EmbeddingRequest;
import com.poc.vectorsearch.dto.EmbeddingResponse;
import com.poc.vectorsearch.dto.PageResponse;
import com.poc.vectorsearch.service.EmbeddingService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;

@RestController
@RequestMapping("/api/v1/embeddings")
@RequiredArgsConstructor
public class EmbeddingController {

    private final EmbeddingService embeddingService;

    @PostMapping
    public ResponseEntity<EmbeddingResponse> create(@Valid @RequestBody EmbeddingRequest request) {
        EmbeddingResponse response = embeddingService.create(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping
    public ResponseEntity<PageResponse<EmbeddingResponse>> findAll(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return ResponseEntity.ok(embeddingService.findPaged(page, size));
    }

    @PostMapping("/batch")
    public ResponseEntity<BulkEmbeddingResponse> bulkCreate(
            @Valid @RequestBody List<@Valid BulkEmbeddingItem> items) {
        if (items == null || items.isEmpty()) {
            return ResponseEntity.badRequest().build();
        }
        return ResponseEntity.ok(embeddingService.bulkCreate(items));
    }

    @PostMapping("/{id}/retry")
    public ResponseEntity<EmbeddingResponse> retry(@PathVariable Long id) {
        EmbeddingResponse response = embeddingService.retry(id);
        return ResponseEntity.accepted().body(response);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        embeddingService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @DeleteMapping
    public ResponseEntity<Void> deleteAll() {
        embeddingService.deleteAll();
        return ResponseEntity.noContent().build();
    }
}
