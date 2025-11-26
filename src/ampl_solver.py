"""
Módulo de interfaz entre Python y AMPL usando amplpy.
Contiene dos componentes principales:
1. solve_optimal: Función standalone para resolver el problema completo de forma exacta (Benchmark).
2. AMPLWrapper: Clase persistente que ayuda a la heurística a evaluar costos rápidamente sin recargar el modelo.
"""

import os
from amplpy import AMPL

def solve_optimal(dat_file_path, mod_file_path, mode, solver="gurobi", timelimit=None, mipgap=None):
    """
    Resuelve el problema CFLP completo (MIP) para encontrar el óptimo matemático verdadero.
    Esta función construye el modelo desde cero, lo resuelve una vez y cierra la instancia.
    Útil para comparar qué tan buena es la solución de la heurística.
    """
    print(f"\n[Solver] Iniciando búsqueda de óptimo verdadero... ")
    print(f"Modelo: {mod_file_path}")
    print(f"Datos: {dat_file_path}")

    ampl = None
    try:
        ampl = AMPL()
        if solver == "gurobi":
            ampl.setOption('solver', solver)
            
            # Construcción dinámica de las opciones para Gurobi.
            # 'outlev=1' muestra el log del solver en consola.
            options_str = 'outlev=1 logfile "./logfile.txt" NodefileStart=1.0 NodefileDir="." '
            
            # Aplicar límites de tiempo o brecha de optimalidad si se especifican
            if timelimit is not None:
                options_str += f"timelimit={timelimit} "
            if mipgap is not None:
                options_str += f"mipgap={mipgap} "

            ampl.setOption('gurobi_options', options_str)
            
        # Cargar modelo (.mod) y datos (.dat)
        ampl.read(mod_file_path)
        ampl.readData(dat_file_path)

        # Resolver el problema de optimización entero mixto (MIP)
        print("[Solver] Resolviendo (esto puede tardar mucho dependiendo de la instancia)...")
        ampl.solve()

        solve_result = ampl.solve_result
        print(f"[solver] Resultado: {solve_result}")

        # Intentar obtener el valor de la función objetivo
        try:
            total_cost = ampl.getObjective('Total_Cost').value()
        except Exception:
            total_cost = None

        # Verificación de validez de la solución
        if total_cost is None or ("optimal" not in solve_result.lower() and "solved" not in solve_result.lower()):
            print("[Solver] No se encontró una solución óptima o factible.")
            if total_cost is not None:
                print(f"[Solver] Retornando mejor solución encontrada (Gap > 0).")
            else:
                return None, None, None
        
        print(f"[Solver] Mejor costo encontrado: {total_cost:,.2f}")
        
        # Extracción de variables de decisión desde AMPL a Python
        facility_var = ampl.getVariable('x') # Variable binaria de apertura
        assignment_var = ampl.getVariable('y') # Variable de asignación
        
        # 1. Filtrar 'x': Identificar qué centros se abrieron (valor > 0.9 para evitar errores de punto flotante)
        facility_vals = facility_var.getValues().toDict()
        open_facilities = [int(j) for j, val in facility_vals.items() if val > 0.9]
        
        print("[Solver] Obteniendo asignaciones...")
        assign_dict = assignment_var.getValues().toDict()

        # 2. Filtrar 'y': Extraer las conexiones cliente -> centro
        assignments = []
        if mode == "SS": # Single Source (Variable binaria)
            threshold = 0.9
            for (i, j), val in assign_dict.items():
                if float(val) > threshold:
                    assignments.append((int(i), int(j)))
        
        elif mode == "MS": # Multi Source (Variable continua 0-1)
            threshold = 1e-6 # Umbral bajo para detectar flujo fraccional
            for (i, j), val in assign_dict.items():
                if float(val) > threshold:
                    assignments.append((int(i), int(j), float(val)))
        
        return total_cost, open_facilities, assignments

    except Exception as e:
        print(f"[Solver] Error en 'solve_optimal': {e}")
        return None, None, None
    finally:
        # Siempre cerrar la instancia de AMPL para liberar memoria y licencias
        if ampl:
            ampl.close()


class AMPLWrapper:
    def __init__(self, dat_file_path, mod_file_path, solver="gurobi", gurobi_opts=None):
        """
        Clase Wrapper para la Heurística.
        CARGA UNICA: Inicializa AMPL, carga el modelo y los datos UNA SOLA VEZ al instanciarse.
        Esto evita la sobrecarga de lectura/escritura en disco en cada iteración de la búsqueda Tabú.
        """
        self.ampl = AMPL()
        self.ampl.setOption('solver', solver)
        
        # solver_msg=0 evita que AMPL imprima en consola cada vez que resolvemos un subproblema (sin mucho éxito).
        self.ampl.setOption('solver_msg', 0) 
        
        if gurobi_opts is None:
            # Configuración rápida por defecto para la heurística:
            # outlev=0 (silencio), 5 seg límite, 5% gap (suficiente para comparar vecinos)
            gurobi_opts = 'outlev=0 timelimit=5.0 mipgap=0.05' 
        self.ampl.setOption('gurobi_options', gurobi_opts)
        
        print("[Wrapper] Leyendo modelo y datos... (esto se hace 1 vez)")
        self.ampl.read(mod_file_path)
        self.ampl.readData(dat_file_path)
        
        # Guardamos referencias a las variables AMPL para acceso rápido luego
        self.facility_var = self.ampl.getVariable('x')
        self.assignment_var = self.ampl.getVariable('y')
        self.total_cost_obj = self.ampl.getObjective('Total_Cost')
        
        # Leer parámetros estáticos (Demanda y Capacidad) para usarlos en la lógica Python
        self.n_locations = int(self.ampl.getParameter('loc').value())
        self.all_locations_indices = list(range(1, self.n_locations + 1))

        try:
            self.demands = self.ampl.getParameter('dem').getValues().toDict()
            self.capacities = self.ampl.getParameter('ICap').getValues().toDict()
        except Exception as e:
            print(f"[Wrapper] ERROR leyendo parámetros: {e}")
            raise e
            
        self.total_demand = sum(self.demands.values())
        
        # Lista ordenada de capacidades para la heurística constructiva
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
        Resuelve el sub-problema de asignación.
        Dado un conjunto fijo de instalaciones abiertas (decidido por Python),
        le pregunta a AMPL cuál es el costo mínimo de transporte.
        
        Usa .fix() en las variables 'x'. Esto transforma el problema de un 
        problema de localización complejo -> A un problema de transporte más simple.
        """
        try:
            open_set = set(open_facilities_indices)
            
            # FIJAR VARIABLES (FIXING):
            # En lugar de cambiar datos, fijamos las variables 'x' a 1 o 0.
            # Esto reduce drásticamente el espacio de búsqueda para Gurobi.
            for j in self.all_locations_indices:
                if j in open_set:
                    self.facility_var[j].fix(1) # Obligatorio abrir
                else:
                    self.facility_var[j].fix(0) # Obligatorio cerrar
            
            # Resolvemos solo la asignación 'y' (y costos fijos de 'x' ya decididos)
            self.ampl.solve()
            
            solve_result = self.ampl.solve_result
            
            # Si la combinación de centros no puede satisfacer la demanda:
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
        """
        Recupera los detalles completos de la asignación (variables 'y')
        para la mejor solución encontrada al final de la heurística.
        """
        # Primero resolvemos (probablemente con mayor precisión configurada fuera de este método)
        final_cost = self.solve_assignment_persistent(open_facilities_indices)

        if final_cost == float('inf'):
            return final_cost, []
        
        try:
            assign_dict = self.assignment_var.getValues().toDict()
        except Exception as e:
            print(f"[Wrapper] Error extrayendo asignación: {e}")
            return final_cost, []
        
        assignments = []
        # Umbral ajustado según el modo
        threshold = 1e-5 if mode == "MS" else 0.9
        
        for (i, j), val in assign_dict.items():
            try:
                if float(val) > threshold:
                    if mode == "SS":
                        assignments.append((int(i), int(j)))
                    else: # MS incluye la fracción de flujo
                        assignments.append((int(i), int(j), float(val)))
            except: pass
        
        return final_cost, assignments

    def close(self):
        # Libera los recursos de AMPL al terminar la ejecución.
        self.ampl.close()