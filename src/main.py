import os
import argparse
import ampl_solver
import heuristic
import utils 

# Rutas
BASE_DIR = os.getcwd() 
DATA_DIR = os.path.join(BASE_DIR, 'data', 'instances_dat')
MOD_DIR = os.path.join(BASE_DIR, 'models')
SOL_DIR = os.path.join(BASE_DIR, 'solutions')
REP_FILE = os.path.join(BASE_DIR, 'report.xlsx')

def get_mod_path(mode):
    if mode == "SS": return os.path.join(MOD_DIR, "CFLP_SingleSource.mod")
    return os.path.join(MOD_DIR, "CFLP_Multisource.mod")

def main(args):
    dat_path = os.path.join(DATA_DIR, f"{args.instance}.dat")
    mod_path = get_mod_path(args.mode)
    
    if not os.path.exists(dat_path):
        print(f"ERROR: No existe {dat_path}. Ejecute el parser primero.")
        return

    # --- Modo Óptimo Exacto ---
    if args.action == 'optimal':
        print(f"--- SOLVING EXACT: {args.instance} ({args.mode}) ---")
        try:
            cost, open_facs, assigns = ampl_solver.solve_exact_full(dat_path, mod_path, args.mode)
            
            if cost is not None:
                utils.save_solution_to_file(SOL_DIR, args.instance, args.mode, cost, open_facs, assigns)
                utils.update_report_excel(REP_FILE, args.instance, args.mode, optimal_cost=cost)
        except Exception as e:
            print(f"CRITICAL ERROR in Exact Solver: {e}")
            import traceback
            traceback.print_exc()

    # --- Modo Heurística ---
    elif args.action == 'heuristic':
        print(f"--- SOLVING HEURISTIC: {args.instance} ({args.mode}) ---")
        
        # 1. Setup Wrapper
        wrapper = ampl_solver.AMPLWrapper(dat_path, mod_path, args.mode)
        
        # 2. Correr Heuristica
        cost, best_open_indices, time_taken = heuristic.run_tabu_search(
            wrapper, 
            max_iter=args.iterations, 
            tenure=args.tenure, 
            sample_size=args.sample
        )
        
        print(f"--- Finalizando... Re-calculando asignación final detallada ---")
        
        # 3. Reconstruir solución final
        final_cost = wrapper.solve_subproblem(best_open_indices)
        _, final_facs, final_assigns = wrapper.get_final_solution_details()
        
        wrapper.close()
        
        # 4. Guardar
        utils.save_solution_to_file(SOL_DIR, args.instance, args.mode, final_cost, final_facs, final_assigns)
        utils.update_report_excel(REP_FILE, args.instance, args.mode, heuristic_cost=final_cost, iterations=args.iterations)
        
        print(f"Done in {time_taken:.2f}s. Cost: {final_cost}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", required=True, choices=['optimal', 'heuristic'])
    parser.add_argument("-i", "--instance", required=True)
    parser.add_argument("-m", "--mode", default="SS", choices=['SS', 'MS'])
    parser.add_argument("-n", "--iterations", type=int, default=50)
    parser.add_argument("-t", "--tenure", type=int, default=10)
    parser.add_argument("-s", "--sample", type=int, default=50)
    
    args = parser.parse_args()
    main(args)