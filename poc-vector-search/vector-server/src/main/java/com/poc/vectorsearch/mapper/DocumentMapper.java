package com.poc.vectorsearch.mapper;

import com.poc.vectorsearch.domain.Document;
import com.poc.vectorsearch.domain.EmbeddingVector;
import com.poc.vectorsearch.dto.SearchResult;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface DocumentMapper {
    void insert(Document document);
    List<Document> findAll();
    List<Document> findPaged(@Param("offset") int offset, @Param("size") int size);
    long countAll();
    Document findById(Long id);
    void deleteById(Long id);
    void deleteAll();
    List<SearchResult> searchByVector(@Param("queryVector") EmbeddingVector queryVector, @Param("topK") int topK, @Param("threshold") double threshold);
}
