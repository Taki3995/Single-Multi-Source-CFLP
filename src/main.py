import os
import argparse
from data_parser import parse_and_convert
import ampl_solver
import utils
import heuristic

# Definir rutas base
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TXT_DIR = os.path.join(DATA_DIR, 'instances_txt')
DAT_DIR = os.path.join(DATA_DIR, 'instances_dat')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
SOLUTIONS_DIR = os.path.join(BASE_DIR, 'solutions')
REPORT_PATH = os.path.join(BASE_DIR, 'report.xlsx')


def get_model_path(mode):
    """Función auxiliar para obtener la ruta del modelo."""
    if mode == "SS":
        mod_file = os.path.join(MODELS_DIR, 'CFLP_SingleSource.mod')
    elif mode == "MS":
        mod_file = os.path.join(MODELS_DIR, 'CFLP_MultiSource.mod')
    else:
        raise ValueError(f"Modo '{mode}' no reconocido. Use 'SS' o 'MS'.")
        
    if not os.path.exists(mod_file):
        raise FileNotFoundError(f"No se encuentra el archivo de modelo: {mod_file}")
    return mod_file

def main(args):
    
    # --- Opción 1: parsear todos los archivos de texto a .dat ---
    if args.action == 'parse':
        print("--- ACCIÓN: Parsear todos los .txt a .dat ---")
        os.makedirs(DAT_DIR, exist_ok=True)
        for f in os.listdir(TXT_DIR):
            if f.endswith(".txt"):
                instance_name = f.replace(".txt", "")
                txt_file = os.path.join(TXT_DIR, f)
                dat_file = os.path.join(DAT_DIR, f"{instance_name}.dat")
                
                if not os.path.exists(dat_file):
                    print(f"Generando {dat_file}...")
                    parse_and_convert(txt_file, dat_file)
                else:
                    print(f"{dat_file} ya existe. Omitiendo.")
        print("--- Parseo Completado ---")
        return

    if not args.instance:
        print("Error: Las acciones 'optimal' y 'heuristic' requieren el argumento -i/--instance.")
        return

    print(f"--- ACCIÓN: {args.action} | INSTANCIA: {args.instance} | MODO: {args.mode} ---")

    # Preparar archivos para esta instancia
    dat_file = os.path.join(DAT_DIR, f"{args.instance}.dat")
    if not os.path.exists(dat_file):
        # Intentar parsear si no existe
        print(f"{dat_file} no existe. Intentando parsear...")
        txt_file = os.path.join(TXT_DIR, f"{args.instance}.txt")
        if not os.path.exists(txt_file):
            print(f"Error: No se encuentra ni {dat_file} ni {txt_file}")
            return
        parse_and_convert(txt_file, dat_file)
    
    mod_file = get_model_path(args.mode)

    # --- Opción 2: Resolver Óptimo Real ---
    if args.action == 'optimal':
        print("\n--- Resolviendo Óptimo (MIP) ---")

        optimal_cost, opt_facilities, opt_assignments = ampl_solver.solve_optimal(
            dat_file, mod_file, args.mode, solver="gurobi", timelimit=None, mipgap=0
        )
        
        if optimal_cost is None:
            optimal_cost = "N/A"

        # Guardar en Excel
        utils.update_report_excel(
            report_path=REPORT_PATH,
            instance_name=args.instance,
            mode=args.mode,
            optimal_cost=optimal_cost
        )
        print("--- Acción 'optimal' Finalizada ---")

    # --- Opción 3: Resolver Heurística ---
    elif args.action == 'heuristic':
        print("\n--- Ejecutando Heurística Híbrida ---")
        
        print("[Main] Creando instancia persistente de AMPLWrapper...")
        gurobi_opts_heuristic = 'outlev=0 LogToConsole=0' # Opciones "silenciosas" para el loop
        try:
            # 1. CREA EL WRAPPER (CARGA DATOS 1 VEZ)
            ampl_wrapper = ampl_solver.AMPLWrapper(
                dat_file, 
                mod_file, 
                solver="gurobi", 
                gurobi_opts=gurobi_opts_heuristic
            )
        except Exception as e:
            print(f"[Main] Error fatal creando AMPLWrapper: {e}")
            return
        
        print("[Main] Instancia cargada. Pasando a la heurística...")

        # 2. LLAMA A LA HEURÍSTICA CON LOS ARGUMENTOS CORRECTOS
        print(f"[Main] N_Locations detectadas: {ampl_wrapper.get_n_locations()}")
        
        # (Define un tamaño de muestra. 500 es un buen inicio para 50x50)
        sample_size = 500
        if "2000x2000" in args.instance:
            sample_size = 1000 # Más grande para instancias más grandes
        
        heuristic_cost, best_facilities, iters_done = heuristic.run_tabu_search(
            ampl_wrapper=ampl_wrapper,  # Pasa el objeto wrapper
            n_locations=ampl_wrapper.get_n_locations(), # Pasa el ENTERO
            max_iterations=args.iterations,
            tabu_tenure_percent=0.10, # 10% de tenencia
            neighborhood_sample_size=sample_size
        )
        
        print(f"[Main] Heurística finalizada. Mejor costo: {heuristic_cost}")

        # 3. Obtener la asignación final para la mejor solución
        if heuristic_cost == float('inf'):
            print("[Main] La heurística no encontró una solución factible.")
            best_assignments = []
        else:
            print("[Main] Obteniendo asignación final para la mejor solución...")
            _ , best_assignments = ampl_wrapper.get_final_solution(best_facilities, args.mode)
        
        # 4. Cerrar la instancia AMPL
        ampl_wrapper.close()
        
        os.makedirs(SOLUTIONS_DIR, exist_ok=True)
        
        # 3. Guardar el archivo de solución
        utils.save_solution_to_file(
            sol_dir=SOLUTIONS_DIR, 
            instance_name=args.instance, 
            mode=args.mode, 
            cost=heuristic_cost, 
            open_facilities=best_facilities, 
            assignments=best_assignments
        )
        
        # 4. Actualizar el Excel
        utils.update_report_excel(
            report_path=REPORT_PATH,
            instance_name=args.instance,
            mode=args.mode,
            heuristic_cost=heuristic_cost,
            iterations=iters_done # Guardamos las iteraciones que realmente hizo
        )
        print("--- Acción 'heuristic' Finalizada ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resolver CFLP con Heurística Híbrida.")
    
    parser.add_argument("-a", "--action", type=str, required=True, 
                        choices=["parse", "optimal", "heuristic"], 
                        help="La tarea a ejecutar")
    
    parser.add_argument("-i", "--instance", type=str, 
                        help="Nombre de la instancia (ej: 2000x2000_1)")
    
    parser.add_argument("-n", "--iterations", type=int, default=100, 
                        help="Número de iteraciones para la heurística")
    
    parser.add_argument("-m", "--mode", type=str, default="SS", 
                        choices=["SS", "MS"], 
                        help="Modo: Single-Source (SS) o Multi-Source (MS)")

    args = parser.parse_args()
    
    main(args)