package com.poc.vectorsearch.domain;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class DocumentChunk {
    private Long id;
    private Long documentId;
    private Integer chunkIndex;
    private Integer chunkTotal;
    private String content;
    private EmbeddingVector embedding;
    private LocalDateTime createdAt;
}
