package com.sehoon.mcp_weather;

import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import com.sehoon.mcp_weather.module.weather.service.WeatherService;

@SpringBootApplication
public class McpWeatherApplication {

  public static void main(String[] args) {
    SpringApplication.run(McpWeatherApplication.class, args);
  }

  @Bean
  public ToolCallbackProvider weatherTools(WeatherService weatherService) {
    return MethodToolCallbackProvider.builder().toolObjects(weatherService).build();
  }
}
