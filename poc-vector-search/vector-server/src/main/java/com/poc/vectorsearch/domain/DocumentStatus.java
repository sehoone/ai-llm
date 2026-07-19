package com.poc.vectorsearch.domain;

public final class DocumentStatus {
    public static final String PENDING    = "pending";
    public static final String PROCESSING = "processing";
    public static final String INDEXED    = "indexed";
    public static final String FAILED     = "failed";

    private DocumentStatus() {}
}
