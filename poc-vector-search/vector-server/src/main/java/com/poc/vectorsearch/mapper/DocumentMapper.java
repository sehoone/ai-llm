package com.poc.vectorsearch.mapper;

import com.poc.vectorsearch.domain.Document;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface DocumentMapper {
    void insert(Document document);
    List<Document> findPaged(@Param("offset") int offset, @Param("size") int size);
    long countAll();
    Document findById(Long id);
    List<Document> findByStatus(@Param("status") String status, @Param("limit") int limit);
    void updateStatus(@Param("id") Long id, @Param("status") String status);
    void updateStatusAndModel(@Param("id") Long id, @Param("status") String status, @Param("model") String model);
    void updateStatusWithError(@Param("id") Long id, @Param("status") String status, @Param("errorMessage") String errorMessage);
    void resetForRetry(Long id);
    int resetStuckProcessing();
    void deleteById(Long id);
    void deleteAll();
}
