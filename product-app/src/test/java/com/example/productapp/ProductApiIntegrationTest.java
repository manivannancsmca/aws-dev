package com.example.productapp;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.mysql.MySQLContainer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * End-to-end test against a REAL MySQL started by Testcontainers (requires Docker).
 * Proves that: Flyway migrations run, Hibernate schema validation passes, and the full CRUD flow works.
 * {@code @ServiceConnection} wires the container's URL/username/password into the Spring DataSource.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class ProductApiIntegrationTest {

    // Same MySQL version as docker-compose.yml, so the tests check what you run locally
    @Container
    @ServiceConnection
    static final MySQLContainer mysql = new MySQLContainer("mysql:8.0.46");

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Test
    void flywayMigrationWasApplied() {
        Integer applied = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM flyway_schema_history WHERE success = 1", Integer.class);
        assertThat(applied).isGreaterThanOrEqualTo(1);

        Integer productsTable = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'products'",
                Integer.class);
        assertThat(productsTable).isEqualTo(1);
    }

    @Test
    void fullCrudLifecycle() throws Exception {
        // CREATE
        MvcResult created = mockMvc.perform(post("/api/products")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name": "Keyboard", "description": "Mechanical", "price": 79.90, "quantity": 20}
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.createdAt").isNotEmpty())
                .andReturn();
        String createdBody = created.getResponse().getContentAsString();
        int id = JsonPath.read(createdBody, "$.id");
        String createdAt = JsonPath.read(createdBody, "$.createdAt");

        // READ
        mockMvc.perform(get("/api/products/{id}", id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Keyboard"))
                .andExpect(jsonPath("$.price").value(79.90));

        // UPDATE
        mockMvc.perform(put("/api/products/{id}", id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name": "Keyboard Pro", "description": "Mechanical, RGB", "price": 99.00, "quantity": 15}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Keyboard Pro"))
                .andExpect(jsonPath("$.quantity").value(15))
                .andExpect(jsonPath("$.createdAt").value(createdAt))
                .andExpect(jsonPath("$.updatedAt").value(not(createdAt)));

        // LIST
        mockMvc.perform(get("/api/products"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[?(@.id == " + id + ")].name").value("Keyboard Pro"));

        // DELETE
        mockMvc.perform(delete("/api/products/{id}", id))
                .andExpect(status().isNoContent());

        // READ again -> 404
        mockMvc.perform(get("/api/products/{id}", id))
                .andExpect(status().isNotFound());
    }
}
