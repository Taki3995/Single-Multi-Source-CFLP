import os
import time
import pandas as pd
from amplpy import AMPL

class AMPLWrapper:
    def __init__(self, dat_file_path, mod_file_path, mode="MS"):
        """
        Inicializa AMPL y carga el modelo una sola vez.
        (Lo utiliza la heurística)
        """
        self.ampl = AMPL()
        self.mode = mode
        
        self.ampl.setOption('solver', 'gurobi')
        
        if mode == "SS":
            # Single Source (Entero)
            gurobi_opts = "outlev=0 threads=0 presolve=2 mipgap=0.01 mipfocus=1 NodefileStart=4.0"
        else:
            # Multi Source (Lineal/Continuo)
            gurobi_opts = "outlev=0 threads=0 presolve=2 method=2 NodefileStart=4.0"

        self.ampl.setOption('gurobi_options', gurobi_opts)

        print(f"[Wrapper] Cargando modelo: {os.path.basename(mod_file_path)}")
        print(f"[Wrapper] Cargando datos: {os.path.basename(dat_file_path)}...")
        
        t0 = time.time()
        self.ampl.read(mod_file_path)
        self.ampl.readData(dat_file_path)
        print(f"[Wrapper] Carga completada")

        self.var_x = self.ampl.getVariable('x')
        self.var_y = self.ampl.getVariable('y')
        self.obj = self.ampl.getObjective('Total_Cost')
        
        # Cache de parámetros
        self.n_locations = int(self.ampl.getParameter('loc').value())
        self.total_demand = 0
        self.capacities = {}
        
        try:
            self.capacities = self.ampl.getParameter('ICap').getValues().toDict()
            self.capacities = {int(k): v for k, v in self.capacities.items()}
            dems = self.ampl.getParameter('dem').getValues().toDict()
            self.total_demand = sum(dems.values())
        except Exception as e:
            print(f"[Wrapper] Error leyendo parámetros: {e}")

        self.all_locs = list(range(1, self.n_locations + 1))

    def calculate_relaxed_lower_bound(self):
        """
        Calcula la Cota Inferior (Lower Bound) relajando el problema.
        Esto nos da un valor de referencia (0% de Gap).
        """
        print("[Wrapper] Calculando Cota Inferior teórica...")
        # Configurar solver para relajación rápida (LP)
        # method=2 es Barrera
        current_opts = self.ampl.getOption('gurobi_options')
        self.ampl.setOption('gurobi_options', "outlev=0 method=2 presolve=2")
        
        # Liberar variables X (unfix) para que el solver decida los mejores centros teóricos
        self.var_x.unfix()
        
        # Relajar integridadd (Solo si estamos en SS, aunque en MS ya es relajado 'y', x sigue binario)
        self.ampl.solve()
        
        # Obtener valor
        try:
            lb = self.obj.value()
        except:
            lb = 0.001 # Evitar división por cero
            
        print(f"[Wrapper] Cota Inferior encontrada: {lb:,.2f}")
        
        # Restaurar opciones
        self.ampl.setOption('gurobi_options', current_opts)
        
        return lb

    def solve_subproblem(self, open_indices):
        """
        Resuelve el subproblema para la heurística.
        """
        try:
            # Fijación rápida de variables
            x_values = {i: 0 for i in self.all_locs}
            for i in open_indices:
                x_values[i] = 1
            self.var_x.setValues(x_values)

            self.ampl.solve()
            
            result = self.ampl.get_value("solve_result")
            # Si es 'infeasible', retornamos infinito
            if result == "infeasible":
                return float('inf')
            
            return self.obj.value()

        except Exception:
            return float('inf')

    def get_final_solution_details(self):
        """
        Extrae la solución completa al final del proceso.
        """
        cost = self.obj.value()
        x_dict = self.var_x.getValues().toDict()
        open_facilities = [int(k) for k, v in x_dict.items() if v > 0.5]
        
        assignments = []
        print("[Wrapper] Extrayendo matriz de asignación...")
        
        y_df = self.var_y.getValues().toPandas()
        
        threshold = 0.001 if self.mode == "MS" else 0.9
        active_assignments = y_df[y_df.iloc[:, 0] > threshold]
        
        for index, row in active_assignments.iterrows():
            cli, loc = index
            val = row[0]
            if self.mode == "SS":
                assignments.append((int(cli), int(loc)))
            else:
                assignments.append((int(cli), int(loc), float(val)))
                
        return cost, open_facilities, assignments

    def close(self):
        self.ampl.close()


def solve_exact_full(dat_path, mod_path, mode):
    """
    Función para resolver el problema completo buscando el óptimo real.
    outlev=1 muestra el log en consola; mipgap=0.0 busca el optimo estricto; 
    threads=0 usa todos los nucleos de la cpu; nodefilestart=4 escribe el arbol en el 
    disco si supera los 4gb.
    """
    wrapper = AMPLWrapper(dat_path, mod_path, mode)
    print("[Exact] Configurando Gurobi para búsqueda de óptimo global...")
    gurobi_opts = "outlev=1 mipgap=0.0 presolve=2 threads=0 NodefileStart=4.0"
    
    wrapper.ampl.setOption('gurobi_options', gurobi_opts)
    
    print("[Exact] Comenzando resolución...")
    
    # Liberar X para que Gurobi decida
    wrapper.var_x.unfix() 
    
    wrapper.ampl.solve()
    
    solve_result = wrapper.ampl.get_value("solve_result")
    print(f"[Exact] Estado final del solver: {solve_result}")

    cost, open_facs, assigns = wrapper.get_final_solution_details()
    wrapper.close()
    return cost, open_facs, assigns