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

def solve_optimal(dat_file_path, mod_file_path, mode, solver="gurobi", timelimit=None, mipgap=None):
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
            
            # Construir opciones dinámicamente
            options_str = 'outlev=1 logfile "./logfile.txt" NodefileStart=1.0 NodefileDir="." '
            
            if timelimit is not None:
                options_str += f"timelimit {timelimit} "
            if mipgap is not None:
                options_str += f"mipgap {mipgap} "

            ampl.setOption( 'gurobi_options', options_str)
            
        # Cargar modelo y datos
        ampl.read(mod_file_path)
        ampl.readData(dat_file_path)

        # Resolver el problema
        print("[Solver] Resolviendo (esto puede tardar mucho dependiendo de la instancia)...")
        ampl.solve()

        solve_result = ampl.solve_result
        print(f"[solver] Resultado: {solve_result}")

        try:
            total_cost = ampl.getObjective('Total_Cost').value()
        except Exception:
            total_cost = None

        if total_cost is None or ("optimal" not in solve_result.lower() and "solved" not in solve_result.lower()):
            print("[Solver] No se encontró una solución óptima o factible.")
            return None, None, None
        
        print(f"[Solver] Mejor costo encontrado: {total_cost:,.2f}")
        
        # Obtener variables de decisión
        facility_var = ampl.getVariable('x') # 'x' son las localizaciones
        assignment_var = ampl.getVariable('y') # 'y' son las asignaciones
        
        # 1. Filtrar 'x' (Centros abiertos)
        facility_vals = facility_var.getValues().toDict()
        open_facilities = [int(j) for j, val in facility_vals.items() if val > 0.9]
        
        print("[Solver] Obteniendo DataFrame de asignaciones...")
        try:
            assign_dict = assignment_var.getValues().toDict()
            print(f"[Solver] Filtrando {len(assign_dict)} asignaciones...")
        except Exception as e:
            print(f"[Solver] ERROR: .toDict() falló: {e}.")
            return total_cost, open_facilities, []

        # 2. Filtrar 'y' (Asignaciones)
        assignments = []
        if mode == "SS":
            print("[Solver] Procesando en modo Single-Source (SS).")
            threshold = 0.9 # Umbral para binario
            for (i, j), val in assign_dict.items():
                try:
                    if float(val) > threshold:
                        assignments.append((int(i), int(j)))
                except (ValueError, TypeError): pass
        
        elif mode == "MS":
            print("[Solver] Procesando en modo Multi-Source (MS).")
            threshold = 1e-6 # Umbral para fraccional (cualquier valor > 0)
            for (i, j), val in assign_dict.items():
                try:
                    if float(val) > threshold:
                        assignments.append((int(i), int(j), float(val)))
                except (ValueError, TypeError): pass
        else:
            print(f"[Solver] Advertencia: Modo '{mode}' no reconocido para procesar asignaciones.")

        print(f"[Solver] Asignaciones filtradas: {len(assignments)}")
        print(f"[Solver] Óptimo encontrado. Costo = {total_cost:,.2f}")
        return total_cost, open_facilities, assignments

    except Exception as e:
        print(f"[Solver] Error en 'solve_optimal': {e}")
        return None, None, None
    finally:
        if ampl:
            ampl.close() # Asegurarse de cerrar AMPL y liberar la licencia


# --- INICIO DE LA CORRECCIÓN (NUEVA FUNCIÓN ROBUSTA) ---
def solve_assignment_robust(dat_file_path, mod_file_path, open_facilities_indices, gurobi_opts):
    """
    Esta función es llamada miles de veces por la heurística.
    Crea una instancia, resuelve y la destruye.
    Es más lenta por llamada, pero NUNCA se colgará.
    """
    ampl = None
    try:
        ampl = AMPL()
        ampl.setOption('solver', 'gurobi')
        ampl.setOption('gurobi_options', gurobi_opts)
        
        # 1. Cargar modelo y datos
        ampl.read(mod_file_path)
        ampl.readData(dat_file_path)
        
        facility_var = ampl.getVariable('x')
        total_cost_obj = ampl.getObjective('Total_Cost')
        n_locations = int(ampl.getParameter('loc').value())
        all_locations_indices = list(range(1, n_locations + 1))
        
        # 2. Fijar las variables 'x' (centros abiertos)
        open_set = set(open_facilities_indices)
        values_dict = {}
        for j in all_locations_indices:
            values_dict[j] = 1.0 if j in open_set else 0.0

        facility_var.set_values(values_dict)
        
        # 3. Resolver
        ampl.solve()
        
        solve_result = ampl.getValue("solve_result")
        
        if solve_result and ("optimal" in str(solve_result).lower() or "solved" in str(solve_result).lower()):
            return total_cost_obj.value()
        else:
            return float('inf') # Solución infactible
            
    except Exception as e:
        return float('inf')
    finally:
        if ampl:
            ampl.close()
class AMPLWrapper:
    def __init__(self, dat_file_path, mod_file_path, solver="gurobi", gurobi_opts=None):
        """
        Carga el modelo y los datos UNA SOLA VEZ al ser instanciado.
        (Solo se usa para leer datos iniciales, no para resolver)
        """
        self.ampl = AMPL()
        self.ampl.setOption('solver', solver)
        if gurobi_opts is None:
            gurobi_opts = 'outlev=0' # Opciones ligeras por defecto para la heurística
        self.ampl.setOption('gurobi_options', gurobi_opts)
        
        print("[Wrapper] Leyendo modelo y datos... (esto se hace 1 vez)")
        self.ampl.read(mod_file_path)
        self.ampl.readData(dat_file_path)
        print("[Wrapper] Modelo y datos cargados.")
        
        # Guardar referencias a las entidades de AMPL
        self.facility_var = self.ampl.getVariable('x')
        self.assignment_var = self.ampl.getVariable('y')
        self.total_cost_obj = self.ampl.getObjective('Total_Cost')
        
        # Guardar N_Locations (para la heurística)
        self.n_locations = int(self.ampl.getParameter('loc').value())
        self.all_locations_indices = list(range(1, self.n_locations + 1))

        print("[Wrapper] Calculando demanda total y capacidades...")
        # (El resto de __init__ no cambia)
        try:
            self.demands = self.ampl.getParameter('dem').getValues().toDict()
            self.capacities = self.ampl.getParameter('ICap').getValues().toDict()
        except Exception as e:
            print(f"[Wrapper] ERROR: No se pudieron leer parámetros 'dem' o 'ICap'. ¿Están en el .dat?")
            raise e
            
        # Calcular demanda total
        self.total_demand = sum(self.demands.values())
        
        # Crear una lista de tuplas (capacidad, indice) para la heurística
        # Ordenada de mayor a menor capacidad
        self.capacity_list = sorted(
            [(cap, int(j)) for j, cap in self.capacities.items() if cap > 0],
            reverse=True 
        )
        print(f"[Wrapper] Demanda Total Detectada: {self.total_demand:,.0f}")
        if not self.capacity_list:
            print("[Wrapper] ADVERTENCIA: No se encontraron capacidades > 0.")

    def get_n_locations(self):
        """Devuelve el número de localizaciones para la heurística."""
        return self.n_locations

    def get_total_demand(self):
        """Retorna la demanda total de todos los clientes."""
        return self.total_demand

    def get_capacity_list(self):
        """Retorna la lista de (capacidad, indice) ordenada."""
        return self.capacity_list

    def get_final_solution(self, open_facilities_indices, mode):
        """
        Se llama una vez al final de la heurística para obtener 
        el costo Y la lista de asignaciones.
        """
        # Obtener el costo final usando el método robusto
        try:
            dat_file = self.ampl.getDataSources()[0]
            mod_file = self.ampl.getModels()[0]
        except Exception as e:
            print(f"Error obteniendo paths de AMPL: {e}")
            return float('inf'), []

        final_cost = solve_assignment_robust(
            dat_file, mod_file, open_facilities_indices, 'outlev=0 LogToConsole=0'
        )

        if final_cost == float('inf'):
            return final_cost, []
        
        print("[Wrapper] Extrayendo asignación final...")
        try:
            # 2. re-resolver en la instancia persistente (1 sola vez)
            open_set = set(open_facilities_indices)
            values_dict = {}
            for j in self.all_locations_indices:
                values_dict[j] = 1.0 if j in open_set else 0.0
            self.facility_var.set_values(values_dict)
            self.ampl.solve() # Esta llamada es segura (solo 1 vez)
            
            assign_dict = self.assignment_var.getValues().toDict()
        except Exception as e:
            print(f"[Wrapper] Error extrayendo asignación final: {e}")
            return final_cost, [] # Error
        
        assignments = []
        threshold = 0.0001 if mode == "MS" else 0.9
        for (i, j), val in assign_dict.items():
            try:
                if float(val) > threshold:
                    if mode == "SS":
                        assignments.append((int(i), int(j)))
                    else: # MS
                        assignments.append((int(i), int(j), float(val)))
            except (ValueError, TypeError):
                pass
        
        return final_cost, assignments

    def close(self):
        """Cierra la instancia de AMPL."""
        try:
            self.ampl.close()
            print("[Wrapper] Instancia AMPL cerrada.")
        except:
            pass