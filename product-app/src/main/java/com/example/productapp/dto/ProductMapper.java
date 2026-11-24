package com.example.productapp.dto;

import com.example.productapp.entity.Product;

/**
 * Converts between the JPA entity and the request/response DTOs.
 * Kept as plain static methods: no extra library (MapStruct etc.) needed for 3 small mappings.
 */
public final class ProductMapper {

    private ProductMapper() {
        // utility class, not meant to be instantiated
    }

    public static Product toEntity(ProductRequest request) {
        Product product = new Product();
        applyRequest(product, request);
        return product;
    }

    /** Copies the editable fields from the request onto an existing entity (used by update). */
    public static void applyRequest(Product product, ProductRequest request) {
        product.setName(request.name());
        product.setDescription(request.description());
        product.setPrice(request.price());
        product.setQuantity(request.quantity());
    }

    public static ProductResponse toResponse(Product product) {
        return new ProductResponse(
                product.getId(),
                product.getName(),
                product.getDescription(),
                product.getPrice(),
                product.getQuantity(),
                product.getCreatedAt(),
                product.getUpdatedAt()
        );
    }
}
