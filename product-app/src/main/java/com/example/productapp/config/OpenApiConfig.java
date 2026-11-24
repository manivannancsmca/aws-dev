package com.example.productapp.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Global information shown at the top of Swagger UI (http://localhost:8080/swagger-ui/index.html).
 * Endpoint-level documentation lives on the controller methods.
 */
@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI productAppOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("Product App API")
                        .version("1.0.0")
                        .description("""
                                REST API for managing products.

                                * All endpoints accept and return JSON.
                                * Validation errors return HTTP 400 with a `fieldErrors` map.
                                * Unknown IDs return HTTP 404.
                                * Health check: `/actuator/health`
                                """)
                        .contact(new Contact().name("Product App Team")));
    }
}
