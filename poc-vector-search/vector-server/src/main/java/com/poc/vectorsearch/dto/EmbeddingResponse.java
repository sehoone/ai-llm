package com.poc.vectorsearch.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class EmbeddingResponse {
    private Long id;
    private String title;
    private String content;       // full_content
    private String sourceType;
    private String status;        // pending | processing | indexed | failed
    private String model;
    private String errorMessage;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
