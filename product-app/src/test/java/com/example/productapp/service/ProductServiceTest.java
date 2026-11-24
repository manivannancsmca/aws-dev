package com.example.productapp.service;

import com.example.productapp.dto.ProductRequest;
import com.example.productapp.dto.ProductResponse;
import com.example.productapp.entity.Product;
import com.example.productapp.exception.ProductNotFoundException;
import com.example.productapp.repository.ProductRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Pure unit tests: the repository is mocked, so no database or Spring context is needed.
 */
@ExtendWith(MockitoExtension.class)
class ProductServiceTest {

    @Mock
    private ProductRepository productRepository;

    @InjectMocks
    private ProductService productService;

    private static ProductRequest sampleRequest() {
        return new ProductRequest("Wireless Mouse", "Ergonomic mouse", new BigDecimal("29.99"), 150);
    }

    private static Product sampleEntity(Long id) {
        Product product = new Product();
        product.setId(id);
        product.setName("Wireless Mouse");
        product.setDescription("Ergonomic mouse");
        product.setPrice(new BigDecimal("29.99"));
        product.setQuantity(150);
        return product;
    }

    @Test
    void create_savesEntityAndReturnsResponse() {
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> {
            Product toSave = invocation.getArgument(0);
            toSave.setId(1L); // simulate the database assigning an ID
            return toSave;
        });

        ProductResponse response = productService.create(sampleRequest());

        assertThat(response.id()).isEqualTo(1L);
        assertThat(response.name()).isEqualTo("Wireless Mouse");
        assertThat(response.price()).isEqualByComparingTo("29.99");
        assertThat(response.quantity()).isEqualTo(150);
    }

    @Test
    void findById_returnsProduct_whenItExists() {
        when(productRepository.findById(1L)).thenReturn(Optional.of(sampleEntity(1L)));

        ProductResponse response = productService.findById(1L);

        assertThat(response.id()).isEqualTo(1L);
        assertThat(response.name()).isEqualTo("Wireless Mouse");
    }

    @Test
    void findById_throwsNotFound_whenMissing() {
        when(productRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productService.findById(99L))
                .isInstanceOf(ProductNotFoundException.class)
                .hasMessage("Product not found with id: 99");
    }

    @Test
    void update_changesFieldsOfExistingProduct() {
        Product existing = sampleEntity(1L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(existing));
        when(productRepository.saveAndFlush(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));
        ProductRequest update = new ProductRequest("Gaming Mouse", null, new BigDecimal("49.50"), 5);

        ProductResponse response = productService.update(1L, update);

        assertThat(response.name()).isEqualTo("Gaming Mouse");
        assertThat(response.description()).isNull();
        assertThat(response.price()).isEqualByComparingTo("49.50");
        assertThat(response.quantity()).isEqualTo(5);
    }

    @Test
    void delete_throwsNotFound_andDoesNotCallDelete_whenMissing() {
        when(productRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productService.delete(99L))
                .isInstanceOf(ProductNotFoundException.class);
        verify(productRepository, never()).delete(any(Product.class));
    }

    @Test
    void delete_removesProduct_whenItExists() {
        Product existing = sampleEntity(1L);
        when(productRepository.findById(1L)).thenReturn(Optional.of(existing));

        productService.delete(1L);

        verify(productRepository).delete(existing);
    }
}
