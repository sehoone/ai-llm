package com.poc.vectorsearch.service;

import com.poc.vectorsearch.domain.Document;
import com.poc.vectorsearch.domain.DocumentChunk;
import com.poc.vectorsearch.domain.DocumentStatus;
import com.poc.vectorsearch.domain.EmbeddingVector;
import com.poc.vectorsearch.mapper.DocumentChunkMapper;
import com.poc.vectorsearch.mapper.DocumentMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class IndexingService {

    private final DocumentMapper documentMapper;
    private final DocumentChunkMapper documentChunkMapper;
    private final TextChunkingService textChunkingService;
    private final OpenAiEmbeddingService openAiEmbeddingService;

    /**
     * 단일 문서를 청킹 → 임베딩 → 저장 순으로 인덱싱한다.
     * 배치 잡과 retry 엔드포인트 양쪽에서 호출한다.
     *
     * 실패 시 status를 'failed'로 기록하고 RuntimeException을 던진다.
     * - 배치: 호출부에서 건별 catch 후 다음 문서 계속 처리
     * - retry: 예외가 HTTP 500으로 전달되어 호출자가 실패를 즉시 인지
     */
    public void index(Document document) {
        log.info("인덱싱 시작 - ID: {}, 제목: {}", document.getId(), document.getTitle());
        documentMapper.updateStatus(document.getId(), DocumentStatus.PROCESSING);

        try {
            // 재처리 시 이전 청크 삭제 (UNIQUE 제약 + 중복 방지)
            documentChunkMapper.deleteByDocumentId(document.getId());

            List<String> chunks = textChunkingService.chunk(document.getFullContent());

            for (int i = 0; i < chunks.size(); i++) {
                String embText = document.getTitle() + " - " + chunks.get(i);
                EmbeddingVector embedding = openAiEmbeddingService.embed(embText);

                DocumentChunk chunk = new DocumentChunk();
                chunk.setDocumentId(document.getId());
                chunk.setChunkIndex(i);
                chunk.setChunkTotal(chunks.size());
                chunk.setContent(chunks.get(i));
                chunk.setEmbedding(embedding);
                documentChunkMapper.insert(chunk);

                log.debug("청크 저장 - 문서 ID: {}, [{}/{}]", document.getId(), i + 1, chunks.size());

                if (i < chunks.size() - 1) {
                    Thread.sleep(300);
                }
            }

            documentMapper.updateStatusAndModel(
                    document.getId(), DocumentStatus.INDEXED, openAiEmbeddingService.getModelName());
            log.info("인덱싱 완료 - ID: {}, 청크: {}개", document.getId(), chunks.size());

        } catch (InterruptedException e) {
            documentMapper.updateStatus(document.getId(), DocumentStatus.PENDING);
            Thread.currentThread().interrupt();
            log.warn("인덱싱 인터럽트 - ID: {} (pending으로 복구)", document.getId());
            throw new RuntimeException("인덱싱이 중단되었습니다.", e);
        } catch (Exception e) {
            documentMapper.updateStatusWithError(document.getId(), DocumentStatus.FAILED, e.getMessage());
            log.error("인덱싱 실패 - ID: {}, 오류: {}", document.getId(), e.getMessage());
            throw new RuntimeException("인덱싱 실패: " + e.getMessage(), e);
        }
    }
}
