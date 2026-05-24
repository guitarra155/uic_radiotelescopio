function unir_figuras()
% UNIR_FIGURAS - Selecciona varias figuras (.fig) y las coloca en una fila.
%
% Descripción:
%   Abre un diálogo para seleccionar archivos .fig.
%   Extrae el contenido (axes) de cada una.
%   Crea una nueva figura con subplots de 1 x N.
%   Copia el contenido y ajusta los títulos.

clc;
disp('--- UNIR FIGURAS AUTOMÁTICO ---');
disp('Por favor, selecciona los archivos .fig que deseas unir.');

% 1. Selección de Archivos
[nombres, ruta] = uigetfile('*.fig', 'Selecciona las Figuras (.fig)', 'MultiSelect', 'on');

if isequal(nombres, 0)
    disp('Cancelado por el usuario.');
    return;
end

% Convertir a cell si es un solo archivo (string)
if ischar(nombres)
    nombres = {nombres};
end

num_figuras = length(nombres);
disp(['Se han seleccionado ' num2str(num_figuras) ' figuras. PROCESANDO...']);

% 2. Crear Figura Principal (Vertical)
fig_final = figure('Name', 'Figuras Unidas', 'Color', 'w', 'Units', 'normalized', 'Position', [0.3 0.05 0.4 0.9]);

for i = 1:num_figuras
    archivo_fig = fullfile(ruta, nombres{i});

    % Abrir figura original (invisible para no molestar)
    f_temp = openfig(archivo_fig, 'invisible');

    % Buscar el 'axes' (el gráfico) dentro de la figura cargada
    ax_orig = findobj(f_temp, 'Type', 'axes');

    if isempty(ax_orig)
        warning(['La figura ' nombres{i} ' no contiene ejes (axes). Se saltará.']);
        close(f_temp);
        continue;
    end

    % Si hay varios axes por figura (ej: subplot), coger el principal o todos
    % Simplificación: Asumimos 1 gráfico principal por figura.
    % Si hay más, tomamos el más grande o el primero encontrado.
    ax_copiar = ax_orig(1);

    % 3. Crear Subplot destino (Vertical: Num_Figuras x 1)
    ax_destino = subplot(num_figuras, 1, i, 'Parent', fig_final);

    % --- COLORES & ALINEACIÓN (Mediana -> -80 dBm) ---
    colores = lines(num_figuras); % Paleta de colores distinta para cada uno
    color_actual = colores(i, :);

    % Buscar línea principal para calcular offset y cambiar color
    lineas = findobj(ax_copiar, 'Type', 'line');
    offset_aplicado = 0;

    if ~isempty(lineas)
        % Asumimos la primera línea es la traza espectral
        y_data = lineas(1).YData;
        ruido_est = median(y_data);
        target_noise = -80;
        offset_aplicado = target_noise - ruido_est;

        % Aplicar Offset y Color a TODAS las líneas del eje (por si hay varias)
        for k = 1:length(lineas)
            lineas(k).YData = lineas(k).YData + offset_aplicado;
            lineas(k).Color = color_actual;
            lineas(k).LineWidth = 1.2; % Un poco más grueso
        end
    end

    % 4. Copiar Contenido MODIFICADO
    copyobj(allchild(ax_copiar), ax_destino);

    % 5. Copiar Propiedades Estéticas
    title(ax_destino, nombres{i}, 'Interpreter', 'none', 'FontSize', 10, 'Color', 'k');
    fprintf('  - %s: Offset aplicado = %.2f dB\n', nombres{i}, offset_aplicado);

    xlabel(ax_destino, ax_copiar.XLabel.String);
    % ylabel(ax_destino, ax_copiar.YLabel.String); % Eliminado para usar eje global
    grid(ax_destino, 'on');

    % Escalas y Limites (Ajustados al nuevo offset)
    xlim(ax_destino, ax_copiar.XLim);

    % Ajustar YLim dinámico (Zoom al pico)
    y_max_global = -inf;
    if ~isempty(lineas)
        for k = 1:length(lineas)
            y_max_local = max(lineas(k).YData);
            if y_max_local > y_max_global
                y_max_global = y_max_local;
            end
        end
    end

    if y_max_global > target_noise
        ylim(ax_destino, [target_noise - 5, y_max_global + 5]);
    else
        ylim(ax_destino, [target_noise - 10, target_noise + 20]); % Fallback
    end

    % Cerrar figura temporal
    close(f_temp);
end

% Eje Y Global (Truco: Axes invisible)
han = axes(fig_final, 'visible', 'off');
han.Title.Visible = 'on';
han.XLabel.Visible = 'on';
han.YLabel.Visible = 'on';
ylabel(han, 'Amplitud (dBm)', 'FontWeight', 'bold');

% Guardamos el objeto título para ajustar su posición
t = title(han, 'Comparación de Figuras');
t.Position(2) = t.Position(2) + 0.05; % Subirlo un poco (ajusta 0.05 según necesidad)

disp('--> ¡Listo! Figura generada.');
end
