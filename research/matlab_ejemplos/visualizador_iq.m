% Guardar como: C:\uic_radiotelescopio\research\matlab_ejemplos\visualizador_iq.m

filename = 'C:\uic_radiotelescopio\data\test_signal.iq';
fs = 2e6;
window_duration = 1.0;

% --- CONFIGURACIÓN DEL FILTRO MOVING AVERAGE ---
ma_samples = 5; % MODIFICAR AQUÍ el número de muestras del filtro

fileID = fopen(filename, 'r');
if fileID == -1
    error('Error al abrir el archivo.');
end
data = fread(fileID, 'int16');
fclose(fileID);

I = data(1:2:end);
Q = data(2:2:end);
signal_iq = complex(I, Q);

% Aplicación del filtro Moving Average
b = ones(1, ma_samples) / ma_samples;
a = 1;
signal_iq_filtered = filter(b, a, signal_iq);

total_samples = length(signal_iq);
total_time = total_samples / fs;

t = (0:total_samples-1) / fs;
window_samples = round(window_duration * fs);
step_samples = round(fs / 20);

if window_samples > total_samples
    window_samples = total_samples;
end

fig_title = sprintf('Visualizador IQ - Total: %.2f s (Espacio pausar)', total_time);
fig = figure('Name', fig_title, 'KeyPressFcn', @keyPressCallback);

ax1 = subplot(2, 1, 1);
hPlotI = plot(ax1, t(1:window_samples), real(signal_iq(1:window_samples)), 'b');
hold(ax1, 'on');
hPlotQ = plot(ax1, t(1:window_samples), imag(signal_iq(1:window_samples)), 'r');
title(ax1, 'Señal Original');
legend(ax1, 'Canal I', 'Canal Q');
ylabel(ax1, 'Amplitud (16-bit)');
grid(ax1, 'on');

ax2 = subplot(2, 1, 2);
hPlotI_filt = plot(ax2, t(1:window_samples), real(signal_iq_filtered(1:window_samples)), 'b');
hold(ax2, 'on');
hPlotQ_filt = plot(ax2, t(1:window_samples), imag(signal_iq_filtered(1:window_samples)), 'r');
title(ax2, sprintf('Señal con Filtro Moving Average (%d muestras)', ma_samples));
xlabel(ax2, 'Tiempo (s)');
ylabel(ax2, 'Amplitud (16-bit)');
legend(ax2, 'Canal I', 'Canal Q');
grid(ax2, 'on');

linkaxes([ax1, ax2], 'xy');

global pause_flag;
pause_flag = false;

for k = 1:step_samples:(total_samples - window_samples)
    if ~ishghandle(fig)
        break;
    end

    while pause_flag
        pause(0.1);
        if ~ishghandle(fig)
            return;
        end
    end

    idx_start = k;
    idx_end = k + window_samples - 1;

    set(hPlotI, 'XData', t(idx_start:idx_end), 'YData', real(signal_iq(idx_start:idx_end)));
    set(hPlotQ, 'XData', t(idx_start:idx_end), 'YData', imag(signal_iq(idx_start:idx_end)));

    set(hPlotI_filt, 'XData', t(idx_start:idx_end), 'YData', real(signal_iq_filtered(idx_start:idx_end)));
    set(hPlotQ_filt, 'XData', t(idx_start:idx_end), 'YData', imag(signal_iq_filtered(idx_start:idx_end)));

    xlim(ax1, [t(idx_start), t(idx_end)]);
    xlim(ax2, [t(idx_start), t(idx_end)]);
    drawnow;
end

function keyPressCallback(~, event)
global pause_flag;
if strcmp(event.Key, 'space')
    pause_flag = ~pause_flag;
end
end