package com.poc.vectorsearch.dto;

import lombok.Data;

import javax.validation.constraints.DecimalMax;
import javax.validation.constraints.DecimalMin;
import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;

@Data
public class SearchRequest {
    @NotBlank
    private String query;

    @Min(1)
    @Max(20)
    private int topK = 5;

    @DecimalMin("0.0")
    @DecimalMax("1.0")
    private double threshold = 0.3;
}
