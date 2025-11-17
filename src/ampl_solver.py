"""
Traductor entre python y AMPL. 
"""

import os 
from amplpy import AMPL, Environment, DataFrame

# ... (función solve_optimal sin cambios) ...

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
        
        # Guardar N_Locations (para la heurística)
        self.n_locations = int(self.ampl.getParameter('loc').value())
        self.all_locations_indices = list(range(1, self.n_locations + 1))

        print("[Wrapper] Calculando demanda total y capacidades...")
        # Obtener todos los parámetros necesarios
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

    def solve_assignment_fixed_x(self, open_facilities_indices):
        """
        Esta es la función que la heurística llamará miles de veces.
        Es muy rápida porque solo fija 'x' y resuelve.
        """
        try:
            open_set = set(open_facilities_indices)
            values_dict = {}
            for j in self.all_locations_indices:
                if j in open_set:
                    values_dict[j] = 1.0
                else:
                    values_dict[j] = 0.0

            self.facility_var.set_values(values_dict)
            
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