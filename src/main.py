import os
import argparse
from data_parser import parse_and_convert
import ampl_solver
import utils
import heuristic

# --- Configuración de Rutas ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TXT_DIR = os.path.join(DATA_DIR, 'instances_txt')
DAT_DIR = os.path.join(DATA_DIR, 'instances_dat')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
SOLUTIONS_DIR = os.path.join(BASE_DIR, 'solutions')
REPORT_PATH = os.path.join(BASE_DIR, 'report.xlsx')

def get_model_path(mode):
    if mode == "SS":
        mod_file = os.path.join(MODELS_DIR, 'cflp_SingleSource.mod')
    elif mode == "MS":
        mod_file = os.path.join(MODELS_DIR, 'cflp_MultiSource.mod')
    else:
        raise ValueError(f"Modo '{mode}' no reconocido.")
        
    if not os.path.exists(mod_file):
        # Fallback de mayúsculas
        if mode == "SS": alt = os.path.join(MODELS_DIR, 'CFLP_SingleSource.mod')
        else: alt = os.path.join(MODELS_DIR, 'CFLP_MultiSource.mod')
        if os.path.exists(alt): return alt
        raise FileNotFoundError(f"No se encuentra el modelo: {mod_file}")
    return mod_file

def main(args):
    
    # --- ACCIÓN 1: Parseo Masivo ---
    if args.action == 'parse':
        print("--- ACCIÓN: Parsear todos los .txt a .dat ---")
        os.makedirs(DAT_DIR, exist_ok=True)
        if not os.path.exists(TXT_DIR):
            print(f"Error: No existe {TXT_DIR}")
            return
        for f in os.listdir(TXT_DIR):
            if f.endswith(".txt"):
                txt = os.path.join(TXT_DIR, f)
                dat = os.path.join(DAT_DIR, f.replace(".txt", ".dat"))
                if not os.path.exists(dat):
                    print(f"Generando {dat}...")
                    parse_and_convert(txt, dat)
        print("--- Parseo Completado ---")
        return

    if not args.instance:
        print("Error: Requiere -i / --instance")
        return

    print(f"--- ACCIÓN: {args.action.upper()} | INSTANCIA: {args.instance} | MODO: {args.mode} ---")

    os.makedirs(DAT_DIR, exist_ok=True)
    dat_file = os.path.join(DAT_DIR, f"{args.instance}.dat")
    
    # Generar .dat si falta
    if not os.path.exists(dat_file):
        print(f"[Main] Creando {dat_file}...")
        txt_file = os.path.join(TXT_DIR, f"{args.instance}.txt")
        if os.path.exists(txt_file):
            parse_and_convert(txt_file, dat_file)
        else:
            print(f"Error Fatal: No existe {txt_file}")
            return
    
    try: mod_file = get_model_path(args.mode)
    except Exception as e: print(e); return

    # --- ACCIÓN 2: Óptimo Exacto ---
    if args.action == 'optimal':
        print("\n[Main] Resolviendo Óptimo con Gurobi...")
        optimal_cost, opt_facilities, opt_assignments = ampl_solver.solve_optimal(
            dat_file, mod_file, args.mode, solver="gurobi", timelimit=None, mipgap=0.0
        )
        
        utils.update_report_excel(REPORT_PATH, args.instance, args.mode, optimal_cost=optimal_cost)
        
        if optimal_cost is not None:
            os.makedirs(SOLUTIONS_DIR, exist_ok=True)
            utils.save_solution_to_file(SOLUTIONS_DIR, f"{args.instance}_OPTIMAL", args.mode, optimal_cost, opt_facilities, opt_assignments)
        print("--- Fin Optimal ---")

    # --- ACCIÓN 3: Heurística ---
    elif args.action == 'heuristic':
        print("\n[Main] Ejecutando Heurística Tabu Search...")
        
        # AJUSTE PARA PC LENTO:
        # timelimit=5.0s: Asegura que Gurobi termine bien cada vecino.
        # mipgap=0.05: 5% es suficiente para comparar.
        gurobi_opts_heuristic = 'outlev=0 timelimit=5.0 mipgap=0.05' 

        try:
            ampl_wrapper = ampl_solver.AMPLWrapper(dat_file, mod_file, solver="gurobi", gurobi_opts=gurobi_opts_heuristic)
        except Exception as e:
            print(f"[Main] Error iniciando AMPL: {e}")
            return
        
        print(f"[Main] Instancia cargada. Locs: {ampl_wrapper.get_n_locations()}")

        heuristic_cost, best_facilities, iters_done = heuristic.run_tabu_search(
            ampl_wrapper, dat_file, mod_file, ampl_wrapper.get_n_locations(),
            args.iterations, args.tenure, args.sample
        )
        
        print(f"[Main] Heurística fin. Mejor costo est.: {heuristic_cost}")

        # Refinamiento final (Alta precisión)
        if heuristic_cost != float('inf'):
            print("[Main] Refinando asignación final...")
            ampl_wrapper.ampl.setOption('gurobi_options', 'outlev=0 timelimit=20.0 mipgap=0.0')
            final_cost, best_assignments = ampl_wrapper.get_final_solution(best_facilities, args.mode)
            if final_cost != float('inf'): heuristic_cost = final_cost 
        else:
            best_assignments = []

        ampl_wrapper.close()
        
        os.makedirs(SOLUTIONS_DIR, exist_ok=True)
        utils.save_solution_to_file(SOLUTIONS_DIR, args.instance, args.mode, heuristic_cost, best_facilities, best_assignments)
        
        utils.update_report_excel(REPORT_PATH, args.instance, args.mode, heuristic_cost=heuristic_cost, iterations=iters_done)
        print("--- Fin Heurística ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", required=True, choices=["parse", "optimal", "heuristic"])
    parser.add_argument("-i", "--instance", type=str)
    parser.add_argument("-m", "--mode", type=str, default="SS", choices=["SS", "MS"])
    parser.add_argument("-n", "--iterations", type=int, default=100)
    parser.add_argument("-t", "--tenure", type=int, default=20)
    parser.add_argument("-s", "--sample", type=int, default=100)
    args = parser.parse_args()
    main(args)