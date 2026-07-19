#include <math.h>
#include <stdlib.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Estructura compleja simple
typedef struct {
    float r;
    float i;
} complex_t;

// Bit-reversal para la FFT de Cooley-Tukey
static void bit_reverse(complex_t* data, int n) {
    int j = 0;
    for (int i = 0; i < n - 1; i++) {
        if (i < j) {
            complex_t temp = data[i];
            data[i] = data[j];
            data[j] = temp;
        }
        int k = n / 2;
        while (k <= j) {
            j -= k;
            k /= 2;
        }
        j += k;
    }
}

// FFT Radix-2 In-place (Forward)
static void fft(complex_t* data, int n) {
    bit_reverse(data, n);
    for (int len = 2; len <= n; len <<= 1) {
        float angle = -2.0 * M_PI / len;
        complex_t wlen;
        wlen.r = cosf(angle);
        wlen.i = sinf(angle);
        
        for (int i = 0; i < n; i += len) {
            complex_t w = {1.0f, 0.0f};
            for (int j = 0; j < len / 2; j++) {
                complex_t u = data[i + j];
                complex_t v = data[i + j + len / 2];
                
                complex_t vw;
                vw.r = v.r * w.r - v.i * w.i;
                vw.i = v.r * w.i + v.i * w.r;
                
                data[i + j].r = u.r + vw.r;
                data[i + j].i = u.i + vw.i;
                
                data[i + j + len / 2].r = u.r - vw.r;
                data[i + j + len / 2].i = u.i - vw.i;
                
                float next_wr = w.r * wlen.r - w.i * wlen.i;
                float next_wi = w.r * wlen.i + w.i * wlen.r;
                w.r = next_wr;
                w.i = next_wi;
            }
        }
    }
}

// Exportar funcion para Python
// Calcula el espectro promedio (batches) y devuelve potencia en dBm
#ifdef _WIN32
__declspec(dllexport)
#endif
void compute_spectrum(
    const float* iq_in,     // Interleaved I/Q floats (size: num_samples * 2)
    int num_samples,        // Número total de samples (pares complejos)
    int fft_size,           // Tamaño de la FFT (debe ser potencia de 2)
    const float* window,    // Arreglo de la ventana (size: fft_size)
    float window_pwr,       // Potencia de la ventana para normalización
    float cal_offset,       // cal_offset_dbm
    float* out_pwr          // Buffer de salida (size: fft_size)
) {
    int batches = num_samples / fft_size;
    if (batches == 0) return;

    // Buffer temporal para FFT
    complex_t* buffer = (complex_t*)malloc(fft_size * sizeof(complex_t));
    
    // Inicializar acumulador de potencia
    float* pwr_avg = (float*)calloc(fft_size, sizeof(float));

    for (int b = 0; b < batches; b++) {
        const float* block = iq_in + (b * fft_size * 2);
        
        // 1. Quitar media (DC block) y aplicar ventana
        float sum_r = 0, sum_i = 0;
        for (int i = 0; i < fft_size; i++) {
            sum_r += block[2*i];
            sum_i += block[2*i + 1];
        }
        float mean_r = sum_r / fft_size;
        float mean_i = sum_i / fft_size;

        for (int i = 0; i < fft_size; i++) {
            buffer[i].r = (block[2*i] - mean_r) * window[i];
            buffer[i].i = (block[2*i + 1] - mean_i) * window[i];
        }

        // 2. Calcular FFT
        fft(buffer, fft_size);

        // 3. Acumular magnitud cuadrada con fftshift
        int half = fft_size / 2;
        for (int i = 0; i < fft_size; i++) {
            int shifted_idx = (i + half) % fft_size;
            float mag2 = buffer[i].r * buffer[i].r + buffer[i].i * buffer[i].i;
            pwr_avg[shifted_idx] += mag2;
        }
    }

    // 4. Normalizar a dBm
    float norm_factor = 1.0f / (batches * window_pwr);
    for (int i = 0; i < fft_size; i++) {
        float val = pwr_avg[i] * norm_factor;
        if (val < 1e-12f) val = 1e-12f;
        out_pwr[i] = 10.0f * log10f(val) + cal_offset;
    }

    free(buffer);
    free(pwr_avg);
}
