package com.example.mcpserver.sample.resource;

import io.modelcontextprotocol.server.McpServerFeatures;
import io.modelcontextprotocol.spec.McpSchema;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * MCP Resource 등록 샘플.
 *
 * Resource는 LLM이 읽을 수 있는 데이터 소스를 URI로 노출한다.
 * 파일, DB 쿼리 결과, 외부 API 응답 등을 클라이언트에 제공할 때 사용한다.
 *
 * Case A: text/plain 정적 리소스  → resource://config/app
 * Case B: application/json 리소스 → resource://info/server
 */
@Configuration
public class SampleResource {

    @Bean
    public List<McpServerFeatures.SyncResourceSpecification> sampleResources() {
        return List.of(appConfigResource(), serverInfoResource());
    }

    // ── Case A: text/plain 정적 리소스 ──────────────────────────────────────────
    private McpServerFeatures.SyncResourceSpecification appConfigResource() {
        var resource = new McpSchema.Resource(
                "resource://config/app",
                "Application Config",
                "Current application configuration values",
                "text/plain",
                null
        );
        return new McpServerFeatures.SyncResourceSpecification(resource, (exchange, req) ->
                new McpSchema.ReadResourceResult(List.of(
                        new McpSchema.TextResourceContents(
                                req.uri(),
                                "text/plain",
                                "server.port=8080\n" +
                                "spring.application.name=spring-ai-mcp-server\n" +
                                "app.version=1.0.0"
                        )
                ))
        );
    }

    // ── Case B: application/json 리소스 ─────────────────────────────────────────
    // 실제 운영에서는 DB 조회 결과나 외부 API 응답을 여기서 반환한다.
    private McpServerFeatures.SyncResourceSpecification serverInfoResource() {
        var resource = new McpSchema.Resource(
                "resource://info/server",
                "Server Info",
                "Runtime information about this MCP server in JSON format",
                "application/json",
                null
        );
        return new McpServerFeatures.SyncResourceSpecification(resource, (exchange, req) ->
                new McpSchema.ReadResourceResult(List.of(
                        new McpSchema.TextResourceContents(
                                req.uri(),
                                "application/json",
                                """
                                {
                                  "name": "Spring AI MCP Server",
                                  "version": "1.0.0",
                                  "transport": "SSE",
                                  "tools": ["greet", "getProduct", "createOrder", "getTodo", "validateAge", "addMemo", "getMemo"]
                                }
                                """
                        )
                ))
        );
    }
}
