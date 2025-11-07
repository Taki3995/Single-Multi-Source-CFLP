"""
Traductor entre python y AMPL. 
"""

import os 
from amplpy import AMPL, Environment, DataFrame

# ----- Configuración del solver -----
# Aseegúrate de que Gurobi (o el solver utilizado) esté en el PATH.
# Si no lo está, descomenta la siguiente linea para añadirlo manualmente
os.environ["PATH"] += os.pathsep + r"C:\gurobi1003\win64\bin"
# ------------------------------------------------------------------------

def solve_optimal(dat_file_path, mod_file_path, solver="gurobi", timelimit=None, mipgap=0):
    """
    Resuelve el problema CFLP completo (MIP) para encontrar el óptimo verdadero.
    Retorna (total_cost, open_facilities_indices, assignments), 
    o en su defecto (None, None, None) si es que fallara.
    """

    print(f"\n[solver] Iniciando búsqueda de óptimo verdadero... ")
    print(f"Modelo: {mod_file_path}")
    print(f"Datos: {dat_file_path}")

    ampl = None # Fuera del try para cerrarlo en 'finally'
    try:
        ampl = AMPL()
        solver_options = f"mipgap={mipgap}"
        if timelimit:
            solver_options += f" timelim={timelimit}"
        
        ampl.setOption(f'{solver}_options', solver_options)

        # Cargar modelo y datos
        ampl.read(mod_file_path)
        ampl.readData(dat_file_path)

        # Resolver el problema
        print("[Solver] Resolviendo...")
        ampl.solve()

        solve_result = ampl.getSolverResult()
        print(f"[solver] Resultado: {solve_result}")

        if "optimal" not in solve_result.lower():
            print("[Solver] No se encontró una solución óptima.")
            return None, None, None
        
        # --- Capturar Resultados ---
        total_cost = ampl.getObjective('Total_Cost').value()
        
        # Obtener variables de decisión
        y_var = ampl.getVariable('y')
        x_var = ampl.getVariable('x')
        
        y_vals = y_var.getValues().toDict()
        x_vals = x_var.getValues().toDict()

        # 1. Filtrar 'y' (Centros abiertos)
        open_facilities = [int(j) for j, val in y_vals.items() if val > 0.9]
        
        # 2. Filtrar 'x' (Asignaciones)
        assignments = []
        if x_var.isBinary():
            # Modo Single-Source: guardar (cliente, centro)
            print("[Solver] Detectado modo Single-Source (x es binaria).")
            assignments = [(int(i), int(j)) for (i, j), val in x_vals.items() if val > 0.9]
        else:
            # Modo Multi-Source: guardar (cliente, centro, fraccion_demanda)
            print("[Solver] Detectado modo Multi-Source (x es continua).")
            assignments = [(int(i), int(j), val) for (i, j), val in x_vals.items() if val > 0.0001]

        print(f"[Solver] Óptimo encontrado. Costo = {total_cost:,.2f}")
        return total_cost, open_facilities, assignments

    except Exception as e:
        print(f"[Solver] Error en 'solve_optimal': {e}")
        return None, None, None
    finally:
        if ampl:
            ampl.close() # Asegurarse de cerrar AMPL y liberar la licencia


def solve_assignment(dat_file_path, mod_file_path, open_facilities_indices, solver="gurobi"):
    """
    Resuelve solo el problema de asignación, dado un conjunto fijo
    de localizaciones abiertas proporcionadas por la heurística.
    Devuelve: costo_total, o en su defecto float('inf') si la solución no es factible.

    No se imprime nada en esta funcion, ya que se llama muchas veces en un 
    bucle, e imprimir ralentizaría el proceso
    """

    ampl = None
    try:
        ampl = AMPL()
        ampl.setOption('solver', solver)
        # Opciones más rápidas, ya que no es un MIP complejo
        ampl.setOption(f'{solver}_options', 'timelim=60') 

        # Cargar modelo y datos
        ampl.read(mod_file_path)
        ampl.readData(dat_file_path)

        # --- FIJAR LAS VARIABLES (El paso clave) ---
        y = ampl.getVariable('y')
        
        # 1. Obtener la lista de TODAS las localizaciones (ej. 1...5000)
        all_locations_indices = ampl.getSet('LOCATIONS').getValues().toList()
        
        # 2. Crear un DataFrame para fijar las variables
        # Esto es MUCHO más rápido que iterar y fijar una por una
        df = DataFrame('LOCATIONS')
        
        # Convertir la lista de la heurística en un Set para búsquedas rápidas
        open_set = set(open_facilities_indices) 
        
        rows = []
        for j in all_locations_indices:
            if j in open_set:
                rows.append((j, 1.0)) # Fija y[j] = 1
            else:
                rows.append((j, 0.0)) # Fija y[j] = 0
        
        df.setValues(rows, ['LOCATIONS', 'y_val'])
        
        # 3. Asignar los valores del DataFrame a la variable 'y'
        y.setValues(df, 'y_val')
        # --- Fin del fijado ---

        # Resolver el subproblema (que ahora es solo de asignación)
        ampl.solve()

        solve_result = ampl.getSolveResult()

        if "optimal" in solve_result.lower():
            total_cost = ampl.getObjective('Total_Cost').value()
            return total_cost
        else:
            # Si la combinación de centros no es factible (ej. no cumple demanda)
            # devolvemos un costo infinito para que la heurística lo descarte.
            return float('inf')

    except Exception as e:
        print(f"[Solver] Error en 'solve_assignment': {e}")
        return float('inf')
    finally:
        if ampl:
            ampl.close() # Siempre cerrar