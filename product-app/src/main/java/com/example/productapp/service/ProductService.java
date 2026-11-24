package com.example.productapp.service;

import com.example.productapp.dto.ProductMapper;
import com.example.productapp.dto.ProductRequest;
import com.example.productapp.dto.ProductResponse;
import com.example.productapp.entity.Product;
import com.example.productapp.exception.ProductNotFoundException;
import com.example.productapp.repository.ProductRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Business logic for products. Controllers call this class; this class calls the repository.
 * Every public method runs inside a database transaction.
 */
@Service
public class ProductService {

    private static final Logger log = LoggerFactory.getLogger(ProductService.class);

    private final ProductRepository productRepository;

    // Constructor injection: Spring passes the repository in, no @Autowired needed
    public ProductService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @Transactional
    public ProductResponse create(ProductRequest request) {
        Product product = ProductMapper.toEntity(request);
        Product saved = productRepository.save(product);
        log.info("Created product id={} name='{}'", saved.getId(), saved.getName());
        return ProductMapper.toResponse(saved);
    }

    @Transactional(readOnly = true)
    public List<ProductResponse> findAll() {
        List<ProductResponse> products = productRepository.findAll().stream()
                .map(ProductMapper::toResponse)
                .toList();
        log.debug("Found {} products", products.size());
        return products;
    }

    @Transactional(readOnly = true)
    public ProductResponse findById(Long id) {
        return ProductMapper.toResponse(getProductOrThrow(id));
    }

    @Transactional
    public ProductResponse update(Long id, ProductRequest request) {
        Product product = getProductOrThrow(id);
        ProductMapper.applyRequest(product, request);
        // saveAndFlush writes the UPDATE immediately (instead of at commit time) so that the
        // @PreUpdate callback has refreshed updatedAt before we build the response.
        Product saved = productRepository.saveAndFlush(product);
        log.info("Updated product id={}", id);
        return ProductMapper.toResponse(saved);
    }

    @Transactional
    public void delete(Long id) {
        Product product = getProductOrThrow(id);
        productRepository.delete(product);
        log.info("Deleted product id={}", id);
    }

    private Product getProductOrThrow(Long id) {
        return productRepository.findById(id)
                .orElseThrow(() -> new ProductNotFoundException(id));
    }
}
