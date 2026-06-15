package com.example.mcpserver.global.config;

import com.example.mcpserver.sample.tool.SampleDbTool;
import com.example.mcpserver.sample.tool.SampleTool;
import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class McpConfig {

    @Bean
    public ToolCallbackProvider mcpToolCallbackProvider(
            SampleTool sampleTool,
            SampleDbTool sampleDbTool
    ) {
        return MethodToolCallbackProvider.builder()
                .toolObjects(sampleTool, sampleDbTool)
                .build();
    }
}
