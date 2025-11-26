import os
import pandas as pd

def save_solution_to_file(sol_dir, instance_name, mode, cost, open_facilities, assignments):
    """
    Guarda la mejor solución encontrada en un archivo de texto.
    Genera un reporte con el costo, centros abiertos y detalles de asignación.
    """
    # Construye la ruta completa del archivo de salida usando el directorio, nombre de instancia y modo (SS/MS)
    filename = os.path.join(sol_dir, f"sol_{instance_name}_{mode}.txt")
    print(f"[Utils] Guardando solución en: {filename}")

    try:
        # Abre el archivo en modo escritura
        with open(filename, 'w') as f:
            # Escribe los metadatos generales de la solución
            f.write(f"Instancia: {instance_name}\n")
            f.write(f"Modo: {mode}\n")
            f.write(f"Costo_Total_Heuristica: {cost}\n\n")

            # Escribe la lista de instalaciones/centros que se decidieron abrir
            f.write("Centros_Abiertos (x):\n")
            f.write(str(open_facilities))
            f.write("\n\n")
            f.write("Asignaciones (y):\n")
            
            # Lógica para detectar el formato de asignación según el problema (Single Source vs Multi Source)
            # Caso 1: Single Source (SS). Las tuplas son de tamaño 2: (cliente, centro)
            if all(isinstance(a, tuple) and len(a) == 2 for a in assignments):
                # Itera sobre cada asignación y la escribe en formato legible
                for cli, loc in assignments:
                    f.write(f"Cliente {cli} -> Centro {loc}\n")
            
            # Caso 2: Multi Source (MS). Las tuplas son de tamaño 3: (cliente, centro, fracción/cantidad)
            elif all(isinstance(a, tuple) and len(a) == 3 for a in assignments):
                # Itera incluyendo el valor de flujo o fracción asignada
                for cli, loc, val in assignments:
                    f.write(f"Cliente {cli} -> Centro {loc} (Valor: {val})\n")
            
            # Caso por defecto: Si el formato no coincide con los anteriores, escribe la estructura tal cual
            else:
                f.write(str(assignments))

    except Exception as e:
        # Captura cualquier error de I/O (ej. permisos, ruta inválida) para no detener la ejecución
        print(f"[utils] Error guardando solución: {e}")

def update_report_excel(report_path, instance_name, mode, optimal_cost=None, heuristic_cost=None, iterations=None):
    """
    Gestiona un archivo Excel para llevar el registro de resultados.
    Si el archivo no existe, lo crea. Si la instancia ya existe, actualiza sus datos; si no, agrega una fila nueva.
    """
    print(f"[Utils] Actualizando reporte: {report_path}")
    
    # Definición de las columnas estándar que tendrá el reporte Excel
    cols = ['Instancia', 'Modo', 'Costo_Optimo', 'Costo_Heuristica', 'Iteraciones_Heuristica']
    
    # 1. Carga del archivo existente o creación de uno nuevo
    if os.path.exists(report_path):
        try:
            # Intenta leer el Excel existente usando openpyxl como motor
            df = pd.read_excel(report_path, engine='openpyxl')
        except Exception as e:
            # Si el archivo está corrupto o no se puede leer, inicia un DataFrame vacío
            print(f"[Utils] Error leyendo Excel. Creando uno nuevo. Error: {e}")
            df = pd.DataFrame(columns=cols)
    else:
        # Si el archivo no existe en disco, crea un DataFrame vacío con las columnas definidas
        df = pd.DataFrame(columns=cols)
        
    # 2. Búsqueda de la fila correspondiente a la Instancia y Modo actuales
    # Crea una máscara booleana para filtrar por nombre de instancia y modo de ejecución
    mask = (df['Instancia'] == instance_name) & (df['Modo'] == mode)
    # Obtiene los índices de las filas que coinciden (debería ser 0 o 1 fila)
    idx_list = df.index[mask].tolist()
    
    if not idx_list:
        # 3a. Si la combinación Instancia/Modo no existe en el Excel
        # Se prepara un diccionario con todos los datos disponibles
        new_row_data = {
            'Instancia': instance_name,
            'Modo': mode,
            'Costo_Optimo': optimal_cost,
            'Costo_Heuristica': heuristic_cost,
            'Iteraciones_Heuristica': iterations
        }
        # Se convierte el diccionario a DataFrame y se concatena al final del DataFrame principal
        new_row_df = pd.DataFrame([new_row_data])
        df = pd.concat([df, new_row_df], ignore_index=True)
        print("[Utils] Fila nueva creada en el reporte.")
        
    else:
        # 3b. Si la fila ya existe, procedemos a actualizarla
        row_index = idx_list[0] # Tomamos el índice de la fila encontrada
        
        # Actualiza selectivamente solo los parámetros que no sean None.
        # Esto permite llamar a la función varias veces para actualizar diferentes métricas sin borrar las anteriores.
        
        if optimal_cost is not None:
            df.loc[row_index, 'Costo_Optimo'] = optimal_cost
            print(f"[Utils] Actualizado 'Costo_Optimo' a: {optimal_cost}")
            
        if heuristic_cost is not None:
            df.loc[row_index, 'Costo_Heuristica'] = heuristic_cost
            print(f"[Utils] Actualizado 'Costo_Heuristica' a: {heuristic_cost}")

        if iterations is not None:
            df.loc[row_index, 'Iteraciones_Heuristica'] = iterations
            print(f"[Utils] Actualizado 'Iteraciones_Heuristica' a: {iterations}")

    # 4. Guardado final del archivo Excel
    try:
        # Sobreescribe el archivo Excel con el DataFrame actualizado, sin incluir el índice numérico
        df.to_excel(report_path, index=False, sheet_name="Resultados")
        print("[Utils] Reporte guardado con éxito.")
    except Exception as e:
        # Error común: El archivo Excel está abierto por el usuario y Windows bloquea la escritura
        print(f"[Utils] ERROR: No se pudo guardar el Excel. ¿Está abierto? Error: {e}")