"""
Traductor entre python y AMPL. 
"""

import os
from amplpy import AMPL

def solve_optimal(dat_file_path, mod_file_path, mode, solver="gurobi", timelimit=None, mipgap=None):
    """
    Resuelve el problema CFLP completo (MIP) para encontrar el óptimo verdadero.
    """
    print(f"\n[Solver] Iniciando búsqueda de óptimo verdadero... ")
    print(f"Modelo: {mod_file_path}")
    print(f"Datos: {dat_file_path}")

    ampl = None
    try:
        ampl = AMPL()
        if solver == "gurobi":
            ampl.setOption('solver', solver)
            
            # Construir opciones dinámicamente
            options_str = 'outlev=1 logfile "./logfile.txt" NodefileStart=1.0 NodefileDir="." '
            
            if timelimit is not None:
                options_str += f"timelimit={timelimit} "
            if mipgap is not None:
                options_str += f"mipgap={mipgap} "

            ampl.setOption('gurobi_options', options_str)
            
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
            if total_cost is not None:
                print(f"[Solver] Retornando mejor solución encontrada (Gap > 0).")
            else:
                return None, None, None
        
        print(f"[Solver] Mejor costo encontrado: {total_cost:,.2f}")
        
        # Obtener variables de decisión
        facility_var = ampl.getVariable('x')
        assignment_var = ampl.getVariable('y')
        
        # 1. Filtrar 'x' (Centros abiertos)
        facility_vals = facility_var.getValues().toDict()
        open_facilities = [int(j) for j, val in facility_vals.items() if val > 0.9]
        
        print("[Solver] Obteniendo asignaciones...")
        assign_dict = assignment_var.getValues().toDict()

        # 2. Filtrar 'y' (Asignaciones)
        assignments = []
        if mode == "SS":
            threshold = 0.9
            for (i, j), val in assign_dict.items():
                if float(val) > threshold:
                    assignments.append((int(i), int(j)))
        
        elif mode == "MS":
            threshold = 1e-6
            for (i, j), val in assign_dict.items():
                if float(val) > threshold:
                    assignments.append((int(i), int(j), float(val)))
        
        return total_cost, open_facilities, assignments

    except Exception as e:
        print(f"[Solver] Error en 'solve_optimal': {e}")
        return None, None, None
    finally:
        if ampl:
            ampl.close()


class AMPLWrapper:
    def __init__(self, dat_file_path, mod_file_path, solver="gurobi", gurobi_opts=None):
        """
        Carga el modelo y los datos UNA SOLA VEZ al ser instanciado.
        """
        self.ampl = AMPL()
        self.ampl.setOption('solver', solver)
        
        # --- CORRECCIÓN VELOCIDAD I/O: SILENCIAR AMPL ---
        self.ampl.setOption('solver_msg', 0) 
        
        if gurobi_opts is None:
            # Fallback seguro
            gurobi_opts = 'outlev=0 timelimit=5.0 mipgap=0.05' 
        self.ampl.setOption('gurobi_options', gurobi_opts)
        
        print("[Wrapper] Leyendo modelo y datos... (esto se hace 1 vez)")
        self.ampl.read(mod_file_path)
        self.ampl.readData(dat_file_path)
        
        self.facility_var = self.ampl.getVariable('x')
        self.assignment_var = self.ampl.getVariable('y')
        self.total_cost_obj = self.ampl.getObjective('Total_Cost')
        
        self.n_locations = int(self.ampl.getParameter('loc').value())
        self.all_locations_indices = list(range(1, self.n_locations + 1))

        try:
            self.demands = self.ampl.getParameter('dem').getValues().toDict()
            self.capacities = self.ampl.getParameter('ICap').getValues().toDict()
        except Exception as e:
            print(f"[Wrapper] ERROR leyendo parámetros: {e}")
            raise e
            
        self.total_demand = sum(self.demands.values())
        
        self.capacity_list = sorted(
            [(cap, int(j)) for j, cap in self.capacities.items() if cap > 0],
            reverse=True 
        )
        print(f"[Wrapper] Demanda Total: {self.total_demand:,.0f} | Locs: {self.n_locations}")

    def get_n_locations(self):
        return self.n_locations

    def get_total_demand(self):
        return self.total_demand

    def get_capacity_list(self):
        return self.capacity_list

    def solve_assignment_persistent(self, open_facilities_indices):
        """
        CORRECCIÓN CRÍTICA: Usa .fix() para obligar al solver a usar 
        SOLO los centros indicados.
        """
        try:
            open_set = set(open_facilities_indices)
            
            # Fijar variables: esto es lo que acelera el proceso
            for j in self.all_locations_indices:
                if j in open_set:
                    self.facility_var[j].fix(1)
                else:
                    self.facility_var[j].fix(0)
            
            self.ampl.solve()
            
            solve_result = self.ampl.solve_result
            
            if "infeasible" in solve_result:
                return float('inf')

            try:
                cost = self.total_cost_obj.value()
                if cost is None: return float('inf')
                return float(cost)
            except:
                return float('inf')

        except Exception as e:
            print(f"[Wrapper] Error en solve_assignment_persistent: {e}")
            return float('inf')

    def get_final_solution(self, open_facilities_indices, mode):
        final_cost = self.solve_assignment_persistent(open_facilities_indices)

        if final_cost == float('inf'):
            return final_cost, []
        
        try:
            assign_dict = self.assignment_var.getValues().toDict()
        except Exception as e:
            print(f"[Wrapper] Error extrayendo asignación: {e}")
            return final_cost, []
        
        assignments = []
        threshold = 1e-5 if mode == "MS" else 0.9
        
        for (i, j), val in assign_dict.items():
            try:
                if float(val) > threshold:
                    if mode == "SS":
                        assignments.append((int(i), int(j)))
                    else: # MS
                        assignments.append((int(i), int(j), float(val)))
            except: pass
        
        return final_cost, assignments

    def close(self):
        self.ampl.close()