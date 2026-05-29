clear all

filePath = fullfile('data', 'test_signal.iq');
sampleRate = 2e6;     
windowSize = 50;       
numSamples = 2000;      

if ~exist(filePath, 'file')
    error('No se encontró el archivo de datos en %s', filePath);
end

% 2. Leer muestras del archivo IQ
fileID = fopen(filePath, 'r');
rawSamples = fread(fileID, numSamples * 2, 'int16');
fclose(fileID);

% Separar canales I y Q, y normalizar
samplesNormalized = double(rawSamples) / 32768.0;
I = samplesNormalized(1:2:end);
Q = samplesNormalized(2:2:end);
iqRaw = I + 1i*Q;

N = length(iqRaw);
samplesAxis = 0:N-1; % Eje de muestras

% 3. Aplicar Filtro Moving Average (Promedio Móvil)
iqFiltered = movmean(iqRaw, windowSize);

% 4. Calcular Espectros de Potencia (FFT)
f = linspace(-sampleRate/2, sampleRate/2, N) / 1e6; % Frecuencia en MHz

% FFT con ventana de Hann para reducir fugas espectrales
windowHann = hann(N);
fftRaw = fftshift(fft(iqRaw .* windowHann));
fftFiltered = fftshift(fft(iqFiltered .* windowHann));

% Espectros en dBFS
psdRaw = 10 * log10((abs(fftRaw).^2) / (N * sum(windowHann.^2)) + 1e-12);
psdFiltered = 10 * log10((abs(fftFiltered).^2) / (N * sum(windowHann.^2)) + 1e-12);

% 5. Graficar (Layout 2x2)
figure('Color', [1 1 1], 'Name', 'Análisis Temporal y Espectral - Plataforma DSP');

% --- Fila 1: Señal Original ---
% Temporal Original (Eje X en Muestras)
subplot(2, 2, 1);
plot(samplesAxis, real(iqRaw), 'Color', [0 0.7 0.9], 'LineWidth', 1.0); hold on;
plot(samplesAxis, imag(iqRaw), 'Color', [0.9 0 0.6], 'LineWidth', 1.0);
title('Señal IQ Original (Tiempo)');
xlabel('Número de Muestra (n)');
ylabel('Amplitud (V)');
legend('I (Real)', 'Q (Imaginario)');
grid on;

% Espectro Original
subplot(2, 2, 2);
plot(f, psdRaw, 'Color', [0 0.5 0.8], 'LineWidth', 1.0);
title('Espectro de Frecuencia Original');
xlabel('Frecuencia (MHz)');
ylabel('Potencia (dBFS)');
grid on;

% --- Fila 2: Señal Filtrada (Moving Average) ---
% Temporal Filtrado (Eje X en Muestras)
subplot(2, 2, 3);
plot(samplesAxis, real(iqFiltered), 'Color', [0 0.6 0], 'LineWidth', 1.2); hold on;
plot(samplesAxis, imag(iqFiltered), 'Color', [0.9 0.5 0], 'LineWidth', 1.2);
title(sprintf('Señal IQ Filtrada (MA: %d)', windowSize));
xlabel('Número de Muestra (n)');
ylabel('Amplitud (V)');
legend('I Filtrado', 'Q Filtrado');
grid on;

% Espectro Filtrado
subplot(2, 2, 4);
plot(f, psdFiltered, 'Color', [0.2 0.7 0.2], 'LineWidth', 1.2);
title('Espectro de Frecuencia Filtrado');
xlabel('Frecuencia (MHz)');
ylabel('Potencia (dBFS)');
grid on;
