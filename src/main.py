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

        optimal_cost, opt_facilities, opt_assignments = ampl_solver.solve_optimal(dat_file, mod_file, solver="gurobi", timelimit=None, mipgap=0)
        
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
        
        # (Aquí llamar al próximo archivo que cree)
        # heuristic_cost, best_facilities, best_assignments = heuristic.run_local_search(
        #     dat_file, mod_file, args.iterations
        # )
        
        # --- (DATOS DE PRUEBA HASTA QUE TENGAMOS heuristic.py) ---
        print(" (Próximo paso: implementar heuristic.py) ")
        heuristic_cost = 999999
        best_facilities = [1, 2, 3]
        best_assignments = [(1,1), (2,1), (3,2)]
        # --- (FIN DATOS DE PRUEBA) ---
        
        os.makedirs(SOLUTIONS_DIR, exist_ok=True)
        
        # Guardar el archivo de solución
        utils.save_solution_to_file(
            sol_dir=SOLUTIONS_DIR, 
            instance_name=args.instance, 
            mode=args.mode, 
            cost=heuristic_cost, 
            open_facilities=best_facilities, 
            assignments=best_assignments
        )
        
        # Actualizar el Excel
        utils.update_report_excel(
            report_path=REPORT_PATH,
            instance_name=args.instance,
            mode=args.mode,
            heuristic_cost=heuristic_cost,
            iterations=args.iterations
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