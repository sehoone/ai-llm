package com.example.mcpserver.sample.prompt;

import io.modelcontextprotocol.server.McpServerFeatures;
import io.modelcontextprotocol.spec.McpSchema;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;
import java.util.Map;

/**
 * MCP Prompt 등록 샘플.
 *
 * Prompt는 클라이언트(LLM)가 호출할 수 있는 재사용 가능한 메시지 템플릿이다.
 * 반환된 메시지를 LLM이 컨텍스트로 주입하거나 대화의 시작점으로 사용한다.
 *
 * Case A: 인수 없는 고정 시스템 프롬프트  → assistant-persona
 * Case B: 인수를 받아 동적으로 구성하는 프롬프트 → greeting-prompt
 */
@Configuration
public class SamplePrompt {

    @Bean
    public List<McpServerFeatures.SyncPromptSpecification> samplePrompts() {
        return List.of(personaPrompt(), greetingPrompt());
    }

    // ── Case A: 인수 없는 고정 시스템 프롬프트 ──────────────────────────────────
    private McpServerFeatures.SyncPromptSpecification personaPrompt() {
        var prompt = new McpSchema.Prompt(
                "assistant-persona",
                "Defines the assistant's technical persona for this MCP server",
                List.of()
        );
        return new McpServerFeatures.SyncPromptSpecification(prompt, (exchange, req) ->
                new McpSchema.GetPromptResult(
                        "Technical assistant persona",
                        List.of(new McpSchema.PromptMessage(
                                McpSchema.Role.ASSISTANT,
                                new McpSchema.TextContent(
                                        "You are a concise technical assistant for a Spring AI MCP demo server. " +
                                        "Answer briefly and focus on practical examples."
                                )
                        ))
                )
        );
    }

    // ── Case B: 인수를 받아 동적으로 구성하는 프롬프트 ─────────────────────────
    private McpServerFeatures.SyncPromptSpecification greetingPrompt() {
        var prompt = new McpSchema.Prompt(
                "greeting-prompt",
                "Generates a greeting request for the given name and language",
                List.of(
                        new McpSchema.PromptArgument("name", "Person's name to greet", Boolean.TRUE),
                        new McpSchema.PromptArgument("language", "Language for greeting (e.g. Korean, English)", Boolean.FALSE)
                )
        );
        return new McpServerFeatures.SyncPromptSpecification(prompt, (exchange, req) -> {
            Map<String, Object> args = req.arguments() != null ? req.arguments() : Map.of();
            String name     = (String) args.getOrDefault("name", "World");
            String language = (String) args.getOrDefault("language", "English");
            return new McpSchema.GetPromptResult(
                    "Greeting prompt result",
                    List.of(new McpSchema.PromptMessage(
                            McpSchema.Role.USER,
                            new McpSchema.TextContent(
                                    "Please greet '" + name + "' warmly in " + language + "."
                            )
                    ))
            );
        });
    }
}
