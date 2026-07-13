package com.poc.vectorsearch.domain;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class Document {
    private Long id;
    private String title;
    private String content;
    private EmbeddingVector embedding;
    private String model;
    private LocalDateTime createdAt;
}
