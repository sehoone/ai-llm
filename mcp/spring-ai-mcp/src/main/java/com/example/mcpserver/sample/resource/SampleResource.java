package com.example.mcpserver.sample.resource;

import io.modelcontextprotocol.server.McpServerFeatures;
import io.modelcontextprotocol.spec.McpSchema;
import org.springframework.beans.factory.annotation.Value;
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

    @Value("${server.port:8080}")
    private int serverPort;

    @Value("${spring.application.name}")
    private String appName;

    @Value("${spring.ai.mcp.server.version}")
    private String mcpVersion;

    @Value("${spring.ai.mcp.server.protocol}")
    private String mcpProtocol;

    @Bean
    public List<McpServerFeatures.SyncResourceSpecification> sampleResources() {
        return List.of(appConfigResource(), serverInfoResource());
    }

    // ── Case A: text/plain 정적 리소스 ──────────────────────────────────────────
    private McpServerFeatures.SyncResourceSpecification appConfigResource() {
        var resource = McpSchema.Resource.builder()
                .uri("resource://config/app")
                .name("Application Config")
                .description("Current application configuration values")
                .mimeType("text/plain")
                .build();
        return new McpServerFeatures.SyncResourceSpecification(resource, (exchange, req) ->
                new McpSchema.ReadResourceResult(List.of(
                        new McpSchema.TextResourceContents(
                                req.uri(),
                                "text/plain",
                                "server.port=" + serverPort + "\n" +
                                "spring.application.name=" + appName + "\n" +
                                "mcp.version=" + mcpVersion
                        )
                ))
        );
    }

    // ── Case B: application/json 리소스 ─────────────────────────────────────────
    // 실제 운영에서는 DB 조회 결과나 외부 API 응답을 여기서 반환한다.
    private McpServerFeatures.SyncResourceSpecification serverInfoResource() {
        var resource = McpSchema.Resource.builder()
                .uri("resource://info/server")
                .name("Server Info")
                .description("Runtime information about this MCP server in JSON format")
                .mimeType("application/json")
                .build();
        return new McpServerFeatures.SyncResourceSpecification(resource, (exchange, req) ->
                new McpSchema.ReadResourceResult(List.of(
                        new McpSchema.TextResourceContents(
                                req.uri(),
                                "application/json",
                                """
                                {
                                  "name": "%s",
                                  "version": "%s",
                                  "transport": "%s"
                                }
                                """.formatted(appName, mcpVersion, mcpProtocol)
                        )
                ))
        );
    }
}
