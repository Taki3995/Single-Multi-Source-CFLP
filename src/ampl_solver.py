import os
import time
import pandas as pd
from amplpy import AMPL

class AMPLWrapper:
    def __init__(self, dat_file_path, mod_file_path, mode="MS"):
        """
        Inicializa AMPL y carga el modelo UNA sola vez.
        Utilizado principalmente por la heurística.
        """
        self.ampl = AMPL()
        self.mode = mode
        
        self.ampl.setOption('solver', 'gurobi')
        
        if mode == "SS":
            # Single Source (Entero)
            # ADVERTENCIA: Sin límite de tiempo, si el subproblema es difícil,
            # la heurística esperará indefinidamente hasta que Gurobi termine.
            gurobi_opts = "outlev=0 threads=0 presolve=2 mipgap=0.01 mipfocus=1 NodefileStart=4.0"
        else:
            # Multi Source (Lineal/Continuo) - Generalmente muy rápido.
            gurobi_opts = "outlev=0 threads=0 presolve=2 method=2 NodefileStart=4.0"

        self.ampl.setOption('gurobi_options', gurobi_opts)

        print(f"[Wrapper] Cargando modelo: {os.path.basename(mod_file_path)}")
        print(f"[Wrapper] Cargando datos: {os.path.basename(dat_file_path)}...")
        
        t0 = time.time()
        self.ampl.read(mod_file_path)
        self.ampl.readData(dat_file_path)
        print(f"[Wrapper] Carga completada en {time.time()-t0:.2f}s")

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
        print("[Wrapper] Extrayendo matriz de asignación (esto puede tomar RAM)...")
        
        # Usamos Pandas para gestión eficiente de memoria
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
    Función para resolver el problema COMPLETO buscando el ÓPTIMO REAL.
    SIN NINGÚN LÍMITE DE TIEMPO.
    """
    wrapper = AMPLWrapper(dat_path, mod_path, mode)
    
    # --- CONFIGURACIÓN PARA ÓPTIMO GLOBAL ---
    # outlev=1: Mostrar log en consola.
    # mipgap=0.0: Buscar el óptimo matemático estricto.
    # threads=0: Usar todos los núcleos de la CPU.
    # NodefileStart=0.5: Protege tu RAM escribiendo el árbol en disco si supera 0.5 GB.
    
    print("[Exact] Configurando Gurobi para búsqueda de óptimo global (Sin límite de tiempo)...")
    
    # Eliminamos timelimit completamente.
    gurobi_opts = "outlev=1 mipgap=0.0 presolve=2 threads=0 NodefileStart=4.0"
    
    wrapper.ampl.setOption('gurobi_options', gurobi_opts)
    
    print("[Exact] Comenzando resolución indefinida... (Usa Ctrl+C si necesitas detenerlo manualmente)")
    
    # Liberar X para que Gurobi decida
    wrapper.var_x.unfix() 
    
    wrapper.ampl.solve()
    
    solve_result = wrapper.ampl.get_value("solve_result")
    print(f"[Exact] Estado final del solver: {solve_result}")

    cost, open_facs, assigns = wrapper.get_final_solution_details()
    wrapper.close()
    return cost, open_facs, assigns