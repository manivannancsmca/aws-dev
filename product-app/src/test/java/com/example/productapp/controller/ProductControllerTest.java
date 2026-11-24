package com.example.productapp.controller;

import com.example.productapp.dto.ProductResponse;
import com.example.productapp.exception.ProductNotFoundException;
import com.example.productapp.service.ProductService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.endsWith;
import static org.hamcrest.Matchers.not;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Web-layer tests: only the controller + exception handler are loaded (no database).
 * The service is replaced by a Mockito mock.
 */
@WebMvcTest(ProductController.class)
class ProductControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private ProductService productService;

    private static ProductResponse sampleResponse() {
        Instant now = Instant.parse("2026-01-15T10:30:00Z");
        return new ProductResponse(1L, "Wireless Mouse", "Ergonomic mouse", new BigDecimal("29.99"), 150, now, now);
    }

    @Test
    void createProduct_returns201WithLocationHeader() throws Exception {
        when(productService.create(any())).thenReturn(sampleResponse());

        mockMvc.perform(post("/api/products")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name": "Wireless Mouse", "description": "Ergonomic mouse", "price": 29.99, "quantity": 150}
                                """))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", endsWith("/api/products/1")))
                .andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.name").value("Wireless Mouse"))
                .andExpect(jsonPath("$.price").value(29.99));
    }

    @Test
    void createProduct_withInvalidBody_returns400WithFieldErrors() throws Exception {
        mockMvc.perform(post("/api/products")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name": "", "price": -1, "quantity": null}
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.message").value("Validation failed"))
                .andExpect(jsonPath("$.fieldErrors.name").value("Name is required"))
                .andExpect(jsonPath("$.fieldErrors.price").value("Price must be zero or positive"))
                .andExpect(jsonPath("$.fieldErrors.quantity").value("Quantity is required"));
    }

    @Test
    void createProduct_withMalformedJson_returns400() throws Exception {
        mockMvc.perform(post("/api/products")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{not valid json"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Malformed JSON request body"));
    }

    @Test
    void getProduct_whenMissing_returns404() throws Exception {
        when(productService.findById(99L)).thenThrow(new ProductNotFoundException(99L));

        mockMvc.perform(get("/api/products/99"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.message").value("Product not found with id: 99"))
                .andExpect(jsonPath("$.path").value("/api/products/99"));
    }

    @Test
    void getProduct_withNonNumericId_returns400() throws Exception {
        mockMvc.perform(get("/api/products/abc"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Invalid value 'abc' for parameter 'id'"));
    }

    @Test
    void getAllProducts_returns200WithList() throws Exception {
        when(productService.findAll()).thenReturn(List.of(sampleResponse()));

        mockMvc.perform(get("/api/products"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].name").value("Wireless Mouse"));
    }

    @Test
    void deleteProduct_returns204() throws Exception {
        doNothing().when(productService).delete(1L);

        mockMvc.perform(delete("/api/products/1"))
                .andExpect(status().isNoContent());
    }

    @Test
    void unknownUrl_returns404WithJsonError() throws Exception {
        // No controller maps this URL, so Spring MVC throws NoResourceFoundException
        mockMvc.perform(get("/api/unknown"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.error").value("Not Found"))
                .andExpect(jsonPath("$.message").value("No endpoint found for GET /api/unknown"))
                .andExpect(jsonPath("$.path").value("/api/unknown"));
    }

    @Test
    void unexpectedError_returns500WithoutLeakingDetails() throws Exception {
        // Simulates a bug or an outage inside the service. The ERROR log with a stack trace
        // that this test prints is expected: the handler logs every unexpected error on purpose.
        when(productService.findAll()).thenThrow(new IllegalStateException("Connection pool exhausted"));

        mockMvc.perform(get("/api/products"))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.status").value(500))
                .andExpect(jsonPath("$.error").value("Internal Server Error"))
                .andExpect(jsonPath("$.message").value("An unexpected error occurred"))
                .andExpect(jsonPath("$.path").value("/api/products"))
                // The internal error text must never reach the client
                .andExpect(content().string(not(containsString("Connection pool exhausted"))));
    }
}
