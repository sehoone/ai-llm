package com.poc.vectorsearch.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ChunkResult {
    private Long id;
    private Long documentId;
    private String title;
    private String content;
    private String fullContent;
    private double score;
    private LocalDateTime createdAt;
    private Integer chunkIndex;
    private Integer chunkTotal;
}
