package com.poc.vectorsearch.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class SearchResult {
    private Long id;
    private String title;
    private String content;
    private double score;
    private LocalDateTime createdAt;
}
