package com.sehoon.mcp_weather;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(properties = { "logging.level.root=INFO", "logging.level.com.sehoon.mcp_weather=INFO" })
class McpWeatherApplicationTests {

  @Test
  void contextLoads() {
  }

}
