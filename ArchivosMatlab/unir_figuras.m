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

% 2. Crear Figura Principal
fig_final = figure('Name', 'Figuras Unidas', 'Color', 'w', 'Units', 'normalized', 'Position', [0.1 0.3 0.8 0.4]);

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

    % 3. Crear Subplot destino
    ax_destino = subplot(1, num_figuras, i, 'Parent', fig_final);

    % 4. Copiar Contenido (Niños: líneas, superficies, textos, etc.)
    copyobj(allchild(ax_copiar), ax_destino);

    % 5. Copiar Propiedades Estéticas (Etiquetas, Grid, Título, Vista, Colores)
    title(ax_destino, nombres{i}, 'Interpreter', 'none', 'FontSize', 10); % Poner nombre de archivo como título
    xlabel(ax_destino, ax_copiar.XLabel.String);
    ylabel(ax_destino, ax_copiar.YLabel.String);
    zlabel(ax_destino, ax_copiar.ZLabel.String);
    grid(ax_destino, ax_copiar.XGrid); % Copiar estado del grid

    % Escalas y Limites
    xlim(ax_destino, ax_copiar.XLim);
    ylim(ax_destino, ax_copiar.YLim);
    if ~isempty(ax_copiar.ZLim)
        zlim(ax_destino, ax_copiar.ZLim);
    end

    view(ax_destino, ax_copiar.View); % Copiar punto de vista (2D vs 3D)

    % Colorbar si tenía
    if ~isempty(findobj(f_temp, 'Type', 'colorbar'))
        colorbar(ax_destino);
        colormap(ax_destino, colormap(ax_copiar));
        if ~isempty(ax_copiar.CLim)
            clim(ax_destino, ax_copiar.CLim);
        end
    end

    % Cerrar figura temporal
    close(f_temp);
end

sgtitle('Comparación de Figuras');
disp('--> ¡Listo! Figura generada.');
end
