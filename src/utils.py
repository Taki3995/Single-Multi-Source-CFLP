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

            f.write("Centros_Abiertos (y):\n")
            f.write(str(open_facilities))
            f.write("\n\n")

            f.write("Asignaciones (x):\n")
            # Para SS (cliente, centro)
            if all(isinstance(a, tuple) and len(a) == 2 for a in assignments):
                # Cliente C es atendido por Centro J
                for cli, loc in assignments:
                    f.write(f"  Cliente {cli} -> Centro {loc}\n")
            
            # Para MS (cliente, centro, fraccion)
            elif all(isinstance(a, tuple) and len(a) == 3 for a in assignments):
                for cli, loc, val in assignments:
                    f.write(f"  Cliente {cli} -> Centro {loc} (Valor: {val})\n")
            else:
                f.write(str(assignments))

    except Exception as e:
        print(f"[utils] Error guardando solución: {e}")

def update_report_excel(report_path, instance_name, mode, optimal_cost, heuristic_cost, iterations):
    """
    Actualiza la planilla Excel con los resultados de esta corrida.
    """
    print(f"[Utils] Actualizando reporte: {report_path}")
    
    # Datos nuevos
    new_data = {
        'Instancia': [instance_name],
        'Modo': [mode],
        'Iteraciones_Heuristica': [iterations],
        'Costo_Optimo': [optimal_cost],
        'Costo_Heuristica': [heuristic_cost]
    }
    new_df = pd.DataFrame(new_data)
    
    # Si el archivo no existe, lo crea.
    if not os.path.exists(report_path):
        new_df.to_excel(report_path, index=False, sheet_name="Resultados")
    else:
        # Si existe, lo lee y añade la nueva fila
        try:
            # Usar 'openpyxl' como motor para leer y escribir .xlsx
            df = pd.read_excel(report_path, engine='openpyxl')
            
            # (Opcional: lógica para evitar duplicados si corres lo mismo)
            
            df = pd.concat([df, new_df], ignore_index=True)
            df.to_excel(report_path, index=False, sheet_name="Resultados")
        except Exception as e:
            print(f"[Utils] Error actualizando Excel: {e}")
            # Si falla, guarda un CSV como respaldo
            new_df.to_csv(report_path.replace('.xlsx', f'_{instance_name}.csv'), index=False)