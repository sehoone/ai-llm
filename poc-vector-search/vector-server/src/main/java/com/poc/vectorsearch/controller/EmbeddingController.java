package com.poc.vectorsearch.controller;

import com.poc.vectorsearch.dto.BulkEmbeddingItem;
import com.poc.vectorsearch.dto.BulkEmbeddingResponse;
import com.poc.vectorsearch.dto.EmbeddingRequest;
import com.poc.vectorsearch.dto.EmbeddingResponse;
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
    public ResponseEntity<List<EmbeddingResponse>> findAll() {
        return ResponseEntity.ok(embeddingService.findAll());
    }

    @PostMapping("/batch")
    public ResponseEntity<BulkEmbeddingResponse> bulkCreate(
            @Valid @RequestBody List<@Valid BulkEmbeddingItem> items) {
        if (items == null || items.isEmpty()) {
            return ResponseEntity.badRequest().build();
        }
        return ResponseEntity.ok(embeddingService.bulkCreate(items));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        embeddingService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
