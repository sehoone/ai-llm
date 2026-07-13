package com.poc.vectorsearch.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class EmbeddingResponse {
    private Long id;
    private String title;
    private String content;
    private String model;
    private LocalDateTime createdAt;
}
