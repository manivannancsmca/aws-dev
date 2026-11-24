package com.example.productapp.controller;

import com.example.productapp.dto.ApiErrorResponse;
import com.example.productapp.dto.ProductRequest;
import com.example.productapp.dto.ProductResponse;
import com.example.productapp.service.ProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import java.net.URI;
import java.util.List;

/**
 * REST endpoints for products. The controller only handles HTTP concerns
 * (paths, status codes, validation trigger) and delegates all logic to {@link ProductService}.
 */
@RestController
@RequestMapping(path = "/api/products", produces = MediaType.APPLICATION_JSON_VALUE)
@Tag(name = "Products", description = "Create, read, update and delete products")
public class ProductController {

    private static final String VALIDATION_ERROR_EXAMPLE = """
            {
              "timestamp": "2026-01-15T10:30:00Z",
              "status": 400,
              "error": "Bad Request",
              "message": "Validation failed",
              "path": "/api/products",
              "fieldErrors": {
                "name": "Name is required",
                "price": "Price must be zero or positive"
              }
            }
            """;

    private static final String NOT_FOUND_EXAMPLE = """
            {
              "timestamp": "2026-01-15T10:30:00Z",
              "status": 404,
              "error": "Not Found",
              "message": "Product not found with id: 99",
              "path": "/api/products/99"
            }
            """;

    private final ProductService productService;

    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    @Operation(summary = "Create a product", description = "Creates a new product and returns it with its generated ID. "
            + "The Location header contains the URL of the new product.")
    // @ApiResponse is repeatable: write one per status code, no @ApiResponses({...}) wrapper needed
    @ApiResponse(responseCode = "201", description = "Product created",
            content = @Content(schema = @Schema(implementation = ProductResponse.class)))
    @ApiResponse(responseCode = "400", description = "Validation failed or malformed JSON",
            content = @Content(schema = @Schema(implementation = ApiErrorResponse.class),
                    examples = @ExampleObject(name = "validation-error", value = VALIDATION_ERROR_EXAMPLE)))
    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<ProductResponse> create(@Valid @RequestBody ProductRequest request) {
        ProductResponse created = productService.create(request);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(created.id())
                .toUri();
        return ResponseEntity.created(location).body(created);
    }

    @Operation(summary = "Retrieve all products")
    @ApiResponse(responseCode = "200", description = "List of products (empty list if none exist)",
            content = @Content(array = @ArraySchema(schema = @Schema(implementation = ProductResponse.class))))
    @GetMapping
    public List<ProductResponse> findAll() {
        return productService.findAll();
    }

    @Operation(summary = "Retrieve a product by ID")
    @ApiResponse(responseCode = "200", description = "Product found",
            content = @Content(schema = @Schema(implementation = ProductResponse.class)))
    @ApiResponse(responseCode = "400", description = "ID is not a number",
            content = @Content(schema = @Schema(implementation = ApiErrorResponse.class)))
    @ApiResponse(responseCode = "404", description = "Product not found",
            content = @Content(schema = @Schema(implementation = ApiErrorResponse.class),
                    examples = @ExampleObject(name = "not-found", value = NOT_FOUND_EXAMPLE)))
    @GetMapping("/{id}")
    public ProductResponse findById(
            @Parameter(description = "Product ID", example = "1") @PathVariable Long id) {
        return productService.findById(id);
    }

    @Operation(summary = "Update a product", description = "Replaces name, description, price and quantity of an existing product.")
    @ApiResponse(responseCode = "200", description = "Product updated",
            content = @Content(schema = @Schema(implementation = ProductResponse.class)))
    @ApiResponse(responseCode = "400", description = "Validation failed or malformed JSON",
            content = @Content(schema = @Schema(implementation = ApiErrorResponse.class),
                    examples = @ExampleObject(name = "validation-error", value = VALIDATION_ERROR_EXAMPLE)))
    @ApiResponse(responseCode = "404", description = "Product not found",
            content = @Content(schema = @Schema(implementation = ApiErrorResponse.class),
                    examples = @ExampleObject(name = "not-found", value = NOT_FOUND_EXAMPLE)))
    @PutMapping(path = "/{id}", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ProductResponse update(
            @Parameter(description = "Product ID", example = "1") @PathVariable Long id,
            @Valid @RequestBody ProductRequest request) {
        return productService.update(id, request);
    }

    @Operation(summary = "Delete a product")
    @ApiResponse(responseCode = "204", description = "Product deleted (no body)")
    @ApiResponse(responseCode = "404", description = "Product not found",
            content = @Content(schema = @Schema(implementation = ApiErrorResponse.class),
                    examples = @ExampleObject(name = "not-found", value = NOT_FOUND_EXAMPLE)))
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @Parameter(description = "Product ID", example = "1") @PathVariable Long id) {
        productService.delete(id);
        return ResponseEntity.noContent().build();
    }
}
