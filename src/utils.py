"""   
Funciones de ayuda
"""

import os

def save_solution_to_file(sol_dir, instance_name, mode, cost, open_facilities, assignments):
    """
    Guarda la mejor solución encontrada en un archivo de texto.
    """
    filename = os.path.join(sol_dir, f"sol_{instance_name}_{mode}.txt")
    try:
        with open(filename, 'w') as f:
            f.write(f"Instancia: {instance_name}\n")
            f.write(f"Modo: {mode}\n")
            f.write(f"Costo_Total_Heuristica: {cost}\n\n")

            f.write("Centros_Abiertos (y):\n")
            f.write(str(open_facilities))
            f.write("\n\n")

            f.write("Asignaciones (x):\n")
            # (Aquí pones la lógica para escribir la matriz de asignación, 
            # que para 5000x5000 debe ser cliente -> centro asignado)
            f.write(str(assignments))
        print(f"[utils] Solución guardada en {filename}")
    except Exception as e:
        print(f"[utils] Error guardando solución: {e}")