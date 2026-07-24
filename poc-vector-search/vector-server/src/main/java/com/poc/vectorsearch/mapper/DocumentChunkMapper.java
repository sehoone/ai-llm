package com.poc.vectorsearch.mapper;

import com.poc.vectorsearch.domain.DocumentChunk;
import com.poc.vectorsearch.domain.EmbeddingVector;
import com.poc.vectorsearch.dto.ChunkResult;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface DocumentChunkMapper {
    void insert(DocumentChunk chunk);
    void deleteByDocumentId(Long documentId);
    List<ChunkResult> searchChunks(
            @Param("queryVector") EmbeddingVector queryVector,
            @Param("limit") int limit
    );
}
