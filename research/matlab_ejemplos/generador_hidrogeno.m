% Guardar como: C:\uic_radiotelescopio\research\matlab_ejemplos\generador_hidrogeno.m

fs = 2e6;
duration = 5;
t = (0:(fs*duration)-1) / fs;

f_hi = 150e3;
signal_pure = exp(1i * 2 * pi * f_hi * t);

% 1. GENERACIÓN DE SEÑAL IDEAL (LIMPIA)
signal_clean = signal_pure / max(max(abs(real(signal_pure))), max(abs(imag(signal_pure))));
signal_scaled_clean = signal_clean * 30000;

data_clean = zeros(1, 2 * length(signal_scaled_clean));
data_clean(1:2:end) = real(signal_scaled_clean);
data_clean(2:2:end) = imag(signal_scaled_clean);

filename_clean = 'C:\uic_radiotelescopio\data\test_signal_clean.iq';
fileID_clean = fopen(filename_clean, 'w');
if fileID_clean == -1
    error('No se pudo crear el archivo de señal limpia.');
end
fwrite(fileID_clean, data_clean, 'int16');
fclose(fileID_clean);

% 2. GENERACIÓN DE SEÑAL CON RUIDO
snr_linear = 0.05;
noise = (randn(size(t)) + 1i * randn(size(t))) * sqrt(1 / (2 * snr_linear));
signal_noisy = signal_pure + noise;

signal_noisy = signal_noisy / max(max(abs(real(signal_noisy))), max(abs(imag(signal_noisy))));
signal_scaled_noisy = signal_noisy * 30000;

data_noisy = zeros(1, 2 * length(signal_scaled_noisy));
data_noisy(1:2:end) = real(signal_scaled_noisy);
data_noisy(2:2:end) = imag(signal_scaled_noisy);

filename_noisy = 'C:\uic_radiotelescopio\data\test_signal_noise.iq';
fileID_noisy = fopen(filename_noisy, 'w');
if fileID_noisy == -1
    error('No se pudo crear el archivo de señal con ruido.');
end
fwrite(fileID_noisy, data_noisy, 'int16');
fclose(fileID_noisy);