package com.poc.vectorsearch.mapper;

import com.poc.vectorsearch.domain.Document;
import com.poc.vectorsearch.dto.SearchResult;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface DocumentMapper {
    void insert(Document document);
    List<Document> findAll();
    Document findById(Long id);
    void deleteById(Long id);
    void deleteAll();
    List<SearchResult> searchByVector(@Param("queryVector") String queryVector, @Param("topK") int topK);
}
