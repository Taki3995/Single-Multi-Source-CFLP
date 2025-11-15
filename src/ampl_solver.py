"""
Traductor entre python y AMPL. 
"""

import os 
from amplpy import AMPL, Environment, DataFrame

# ----- Configuración del solver -----
# Asegura que Gurobi (o el solver utilizado) esté en el PATH.
# Si no lo está, descomenta la siguiente linea para añadirlo manualmente
# os.environ["PATH"] += os.pathsep + r"C:\gurobi1003\win64\bin"
# ------------------------------------------------------------------------

def solve_optimal(dat_file_path, mod_file_path, mode, solver="gurobi", timelimit=None, mipgap=0):
    """
    Resuelve el problema CFLP completo (MIP) para encontrar el óptimo verdadero.
    Retorna (total_cost, open_facilities_indices, assignments), 
    o en su defecto (None, None, None) si es que fallara.
    """

    print(f"\n[Solver] Iniciando búsqueda de óptimo verdadero... ")
    print(f"Modelo: {mod_file_path}")
    print(f"Datos: {dat_file_path}")

    ampl = None # Fuera del try para cerrarlo en 'finally'
    try:
        ampl = AMPL()
        if solver == "gurobi":
            ampl.setOption('solver', solver)
            ampl.setOption( 'gurobi_options',  
                            'outlev=1 mipgap 0.01 ' + 
                            'logfile "./logfile.txt" ' + 
                            'NodefileStart=1.0 NodefileDir="."')
        # Cargar modelo y datos
        ampl.read(mod_file_path)
        ampl.readData(dat_file_path)

        # Resolver el problema
        print("[Solver] Resolviendo (esto puede tardar mucho dependiendo de la instancia)...")
        ampl.solve()

        solve_result = ampl.solve_result
        print(f"[solver] Resultado: {solve_result}")

        if "optimal" not in solve_result.lower() and "solved" not in solve_result.lower():
            print("[Solver] No se encontró una solución óptima.")
            return None, None, None
        
        # --- Capturar Resultados ---
        total_cost = ampl.getObjective('Total_Cost').value()
        
        # Obtener variables de decisión
        facility_var = ampl.getVariable('x') # 'x' son las localizaciones
        assignment_var = ampl.getVariable('y') # 'y' son las asignaciones
        
        # 1. Filtrar 'x' (Centros abiertos)
        facility_vals = facility_var.getValues().toDict()
        open_facilities = [int(j) for j, val in facility_vals.items() if val > 0.9]
        
        # --- OPTIMIZACIÓN DE MEMORIA --- 
        print("[Solver] Obteniendo DataFrame de asignaciones...")
        assignment_df = assignment_var.getValues().toPandas() # toPandas() para manejar datos dispersos eficientemente
        print(f"[Solver] Filtrando {len(assignment_df)} asignaciones...")
        
        # --- INICIO DE CORRECCIÓN DE BUG ---
        # El filtro > 0.9 es incorrecto para Multi-Source (MS), 
        # donde y puede ser 0.3, 0.5, etc.
        # Usamos 1e-6 (una tolerancia pequeña) para capturar cualquier
        # asignación positiva.
        filter_tolerance = 1e-6
        assignment_df_filtered = assignment_df[assignment_df.iloc[:, 0] > filter_tolerance]
        # --- FIN DE CORRECCIÓN DE BUG ---

        print(f"[Solver] Asignaciones filtradas: {len(assignment_df_filtered)}")
        
        # 2. Filtrar 'y' (Asignaciones)
        assignments = []
        if mode == "SS":
            print("[Solver] Procesando en modo Single-Source (SS).")
            # Filtramos > 0.9 por si acaso el solver da 0.9999
            df_ss = assignment_df[assignment_df.iloc[:, 0] > 0.9] 
            assignments = [(int(i), int(j)) for (i, j) in df_ss.index] # (i, j) es el índice del dataframe
        
        elif mode == "MS":
            print("[Solver] Procesando en modo Multi-Source (MS).")
            # Aquí usamos el dataframe filtrado con 1e-6
            assignments = [(int(i), int(j), val) for (i, j), val in assignment_df_filtered.iloc[:, 0].to_dict().items()]
        else:
            print(f"[Solver] Advertencia: Modo '{mode}' no reconocido para procesar asignaciones.")

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
    Se usa dentro del bucle de la heurística.
    Devuelve: costo_total, o en su defecto float('inf') si la solución no es factible.
    """

    ampl = None
    try:
        ampl = AMPL()
        ampl.setOption('solver', solver) 
        if solver == "gurobi":
            ampl.setOption('gurobi_options', 'outlev=0') # outlev=0 para modo silencioso
        # Cargar modelo y datos
        ampl.read(mod_file_path)
        ampl.readData(dat_file_path)

        facility_var = ampl.getVariable('x')
        
        # 1. Obtener la lista de todas las localizaciones
        try:
            all_locations_indices = ampl.getSet('LOCATIONS').getValues().toList()
        except:
            # Si el .dat no define el set 'LOCATIONS', lo leemos del param 'loc'
            # print("[Solver-H] Advertencia: Set 'LOCATIONS' no encontrado. Usando 1..loc.")
            loc_count = int(ampl.getParameter('loc').value())
            all_locations_indices = list(range(1, loc_count + 1))

        # 2. Crear un DataFrame para fijar las variables
        df = DataFrame('LOCATIONS')
        
        # Convertir la lista de la heurística en un Set para búsquedas rápidas
        open_set = set(open_facilities_indices) 
        
        rows = []
        for j in all_locations_indices:
            if j in open_set:
                rows.append((j, 1.0))
            else:
                rows.append((j, 0.0))
        
        df.setValues(rows, ['LOCATIONS', 'x_val'])
        
        # 3. Asignar los valores del DataFrame a la variable 'x'
        # Esto "fija" la variable x a los valores dados
        facility_var.setValues(df, 'x_val')

        # Resolver el subproblema (asignación)
        ampl.solve()

        solve_result = ampl.solve_result

        if "optimal" in solve_result.lower() or "solved" in solve_result.lower():
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

def solve_assignment_and_get_solution(dat_file_path, mod_file_path, open_facilities_indices, mode, solver="gurobi"):
    """
    Se llama al final de la búsqueda Tabú.
    Recibe el mejor vector de centros que encontró la heurística para darsela a ampl.
    Devuelve: El costo total. 
    Para reportar.
    """
    print(f"\n[Solver] Obteniendo asignaciones finales para la mejor solución de la heurística...")

    ampl = None
    try:
        ampl = AMPL()
        ampl.setOption('solver', solver) 
        if solver == "gurobi":
            ampl.setOption('gurobi_options', 'outlev=0') 
        
        ampl.read(mod_file_path)
        ampl.readData(dat_file_path)

        facility_var = ampl.getVariable('x')
        assignment_var = ampl.getVariable('y')

        # 1. Fijar las variables 'x'
        try:
            loc_count = int(ampl.getParameter('loc').value())
            all_locations_indices = list(range(1, loc_count + 1))
        except Exception as e:
            print(f"[Solver] Error obteniendo 'loc' count: {e}")
            return None, None
            
        df = DataFrame('LOCATIONS')
        open_set = set(open_facilities_indices) 
        rows = []
        for j in all_locations_indices:
            rows.append((j, 1.0 if j in open_set else 0.0))
        df.setValues(rows, ['LOCATIONS', 'x_val'])
        facility_var.setValues(df, 'x_val')

        # 2. Resolver
        ampl.solve()

        solve_result = ampl.solve_result
        if "optimal" not in solve_result.lower() and "solved" not in solve_result.lower():
            print("[Solver] Error: La solución final de la heurística resultó ser infactible.")
            return None, None

        # 3. Extraer resultados (costo y asignaciones 'y')
        total_cost = ampl.getObjective('Total_Cost').value()
        
        assignment_df = assignment_var.getValues().toPandas()
        
        filter_tolerance = 1e-6
        assignment_df_filtered = assignment_df[assignment_df.iloc[:, 0] > filter_tolerance]
        
        assignments = []
        if mode == "SS":
            df_ss = assignment_df[assignment_df.iloc[:, 0] > 0.9] 
            assignments = [(int(i), int(j)) for (i, j) in df_ss.index]
        elif mode == "MS":
            assignments = [(int(i), int(j), val) for (i, j), val in assignment_df_filtered.iloc[:, 0].to_dict().items()]
        
        print(f"[Solver] Asignaciones finales obtenidas. Costo: {total_cost:,.2f}")
        return total_cost, assignments

    except Exception as e:
        print(f"[Solver] Error en 'solve_assignment_and_get_solution': {e}")
        return None, None
    finally:
        if ampl:
            ampl.close()