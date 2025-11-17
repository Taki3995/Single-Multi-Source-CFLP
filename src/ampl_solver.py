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
class AMPLWrapper:
    def __init__(self, dat_file_path, mod_file_path, solver="gurobi", gurobi_opts=None):
        """
        Carga el modelo y los datos UNA SOLA VEZ al ser instanciado.
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
        
        # Guardar N_Locations (para la heurística) y crear un DF reutilizable
        self.n_locations = int(self.ampl.getParameter('loc').value())
        self.all_locations_indices = list(range(1, self.n_locations + 1))
        
        self.fix_x_df = DataFrame('LOCATIONS')
        self.fix_x_df.set_column('LOCATIONS', self.all_locations_indices)

    def get_n_locations(self):
        """Devuelve el número de localizaciones para la heurística."""
        return self.n_locations

    def solve_assignment_fixed_x(self, open_facilities_indices):
        """
        Funcion que la heurísticallama. Fija x y resuelve.
        """
        try:
            open_set = set(open_facilities_indices)
            
            # 1. Fijar variables 'x'
            x_values = [1.0 if j in open_set else 0.0 for j in self.all_locations_indices]
            self.fix_x_df.set_column('x_val', x_values)
            self.facility_var.setValues(self.fix_x_df, 'x_val')
            
            # 2. Resolver
            self.ampl.solve()
            
            solve_result = self.ampl.getValue("solve_result")
            
            if solve_result and ("optimal" in str(solve_result).lower() or "solved" in str(solve_result).lower()):
                return self.total_cost_obj.value()
            else:
                return float('inf') # Solución infactible
        except Exception as e:
            print(f"[Wrapper] Error en solve_assignment_fixed_x: {e}")
            return float('inf')

    def get_final_solution(self, open_facilities_indices, mode):
        """
        Se llama una vez al final de la heurística para obtener 
        el costo Y la lista de asignaciones.
        """
        # Resuelve una última vez para asegurarse que 'y' está actualizada
        final_cost = self.solve_assignment_fixed_x(open_facilities_indices)
        if final_cost == float('inf'):
            return final_cost, []
        
        print("[Wrapper] Extrayendo asignación final...")
        try:
            assign_dict = self.assignment_var.getValues().toDict()
        except Exception as e:
            print(f"[Wrapper] Error extrayendo asignación final: {e}")
            return final_cost, []
        
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