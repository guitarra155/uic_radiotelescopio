#include <cmath>

extern "C" {
    // Calcula la potencia media lineal y la convierte a dBFS
    __declspec(dllexport) double calcular_potencia_promedio(const double* raw_spectrum, int size) {
        double suma_lineal = 0.0;
        for (int i = 0; i < size; ++i) {
            // Conversión de logarítmico (dBFS) a lineal
            suma_lineal += std::pow(10.0, raw_spectrum[i] / 10.0);
        }
        double promedio_lineal = suma_lineal / size;
        
        // Conversión final a dBFS
        return 10.0 * std::log10(promedio_lineal);
    }
}
