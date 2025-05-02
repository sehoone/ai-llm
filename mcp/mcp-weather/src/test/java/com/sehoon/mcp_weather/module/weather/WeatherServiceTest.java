package com.sehoon.mcp_weather.module.weather;

import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.web.client.RestClient;

import com.sehoon.mcp_weather.module.weather.service.WeatherService;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.transport.ServerParameters;
import io.modelcontextprotocol.client.transport.StdioClientTransport;
import io.modelcontextprotocol.spec.McpSchema.CallToolRequest;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpSchema.ListToolsResult;
import lombok.extern.slf4j.Slf4j;

import java.util.Map;

@Slf4j
@SpringBootTest
class WeatherServiceTest {

  @InjectMocks
  private WeatherService weatherService;

  @Mock
  private RestClient restClient;

  @Test
  void testGetWeatherForecastByLocation() {
    // Initialize mocks
    var stdioParams = ServerParameters.builder("java")
        .args("-jar", "D:\\dev\\vscodeWorkspace\\ai-llm\\mcp\\mcp-weather\\target\\mcp-weather-0.0.1-SNAPSHOT.jar")
        .build();

    var stdioTransport = new StdioClientTransport(stdioParams);

    var mcpClient = McpClient.sync(stdioTransport).build();

    mcpClient.initialize();

    // List available tools
    ListToolsResult toolsList = mcpClient.listTools();
    log.info("Available tools: " + toolsList);

    // Call the weather forecast tool
    CallToolResult weather = mcpClient.callTool(
        new CallToolRequest("getWeatherForecastByLocation",
            Map.of("latitude", "47.6062", "longitude", "-122.3321")));
    log.info("Weather forecast result: " + weather);

    // Call the alerts tool
    CallToolResult alert = mcpClient.callTool(
        new CallToolRequest("getAlerts", Map.of("state", "NY")));
    log.info("Weather alert result: " + alert);

    // Close the client gracefully
    mcpClient.closeGracefully();
  }
}