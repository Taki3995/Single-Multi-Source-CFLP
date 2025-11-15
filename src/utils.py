"""   
Funciones de ayuda
"""

import os
import pandas as pd

def save_solution_to_file(sol_dir, instance_name, mode, cost, open_facilities, assignments):
    """
    Guarda la mejor solución encontrada en un archivo de texto.
    """
    filename = os.path.join(sol_dir, f"sol_{instance_name}_{mode}.txt")
    print(f"[Utils] Guardando solución en: {filename}")

    try:
        with open(filename, 'w') as f:
            f.write(f"Instancia: {instance_name}\n")
            f.write(f"Modo: {mode}\n")
            f.write(f"Costo_Total_Heuristica: {cost}\n\n")

            f.write("Centros_Abiertos (x):\n")
            f.write(str(open_facilities))
            f.write("\n\n")
            f.write("Asignaciones (y):\n")
            
            # Para SS (cliente, centro)
            if all(isinstance(a, tuple) and len(a) == 2 for a in assignments):
                # Cliente C es atendido por Centro J
                for cli, loc in assignments:
                    f.write(f"  Cliente {cli} -> Centro {loc}\n")
            
            # Para MS (cliente, centro, fraccion)
            elif all(isinstance(a, tuple) and len(a) == 3 for a in assignments):
                for cli, loc, val in assignments:
                    f.write(f"  Cliente {cli} -> Centro {loc} (Valor: {val})\n")
            else:
                f.write(str(assignments))

    except Exception as e:
        print(f"[utils] Error guardando solución: {e}")

def update_report_excel(report_path, instance_name, mode, optimal_cost=None, heuristic_cost=None, iterations=None):
    """
    Lee, actualiza y guarda la planilla Excel.
    Busca la fila por (instance, mode) y actualiza las columnas
    correspondientes. Si no existe, crea la fila.
    """
    print(f"[Utils] Actualizando reporte: {report_path}")
    
    # Columnas que esperamos
    cols = ['Instancia', 'Modo', 'Costo_Optimo', 'Costo_Heuristica', 'Iteraciones_Heuristica']
    
    # 1. Leer el archivo (o crear un DataFrame vacío)
    if os.path.exists(report_path):
        try:
            df = pd.read_excel(report_path, engine='openpyxl')
        except Exception as e:
            print(f"[Utils] Error leyendo Excel. Creando uno nuevo. Error: {e}")
            df = pd.DataFrame(columns=cols)
    else:
        df = pd.DataFrame(columns=cols)
        
    # 2. Buscar la fila
    # (mask = máscara booleana)
    mask = (df['Instancia'] == instance_name) & (df['Modo'] == mode)
    idx_list = df.index[mask].tolist()
    
    if not idx_list:
        # 3a. No existe la fila: Crear una nueva
        new_row_data = {
            'Instancia': instance_name,
            'Modo': mode,
            'Costo_Optimo': optimal_cost,
            'Costo_Heuristica': heuristic_cost,
            'Iteraciones_Heuristica': iterations
        }
        new_row_df = pd.DataFrame([new_row_data])
        df = pd.concat([df, new_row_df], ignore_index=True)
        print("[Utils] Fila nueva creada en el reporte.")
        
    else:
        # 3b. Existe la fila: Actualizarla
        row_index = idx_list[0]
        
        # Actualiza solo los valores que se pasaron (que no son None)
        if optimal_cost is not None:
            df.loc[row_index, 'Costo_Optimo'] = optimal_cost
            print(f"[Utils] Actualizado 'Costo_Optimo' a: {optimal_cost}")
            
        if heuristic_cost is not None:
            df.loc[row_index, 'Costo_Heuristica'] = heuristic_cost
            print(f"[Utils] Actualizado 'Costo_Heuristica' a: {heuristic_cost}")

        if iterations is not None:
            df.loc[row_index, 'Iteraciones_Heuristica'] = iterations
            print(f"[Utils] Actualizado 'Iteraciones_Heuristica' a: {iterations}")

    # 4. Guardar el archivo
    try:
        df.to_excel(report_path, index=False, sheet_name="Resultados")
        print("[Utils] Reporte guardado con éxito.")
    except Exception as e:
        print(f"[Utils] ERROR: No se pudo guardar el Excel. ¿Está abierto? Error: {e}")