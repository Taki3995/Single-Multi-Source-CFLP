import os
import argparse
from data_parser import parse_and_convert
import ampl_solver
import utils
import heuristic

# --- Configuración de Rutas (Cross-Platform) ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TXT_DIR = os.path.join(DATA_DIR, 'instances_txt')
DAT_DIR = os.path.join(DATA_DIR, 'instances_dat')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
SOLUTIONS_DIR = os.path.join(BASE_DIR, 'solutions')
REPORT_PATH = os.path.join(BASE_DIR, 'report.xlsx')

def get_model_path(mode):
    """Retorna la ruta del modelo AMPL según el modo (SS o MS)."""
    if mode == "SS":
        mod_file = os.path.join(MODELS_DIR, 'cflp_SingleSource.mod')
    elif mode == "MS":
        mod_file = os.path.join(MODELS_DIR, 'cflp_MultiSource.mod')
    else:
        raise ValueError(f"Modo '{mode}' no reconocido. Use 'SS' o 'MS'.")
        
    if not os.path.exists(mod_file):
        # Intento de fallback por si el nombre del archivo tiene mayúsculas/minúsculas distintas
        if mode == "SS": alternative = os.path.join(MODELS_DIR, 'CFLP_SingleSource.mod')
        else: alternative = os.path.join(MODELS_DIR, 'CFLP_MultiSource.mod')
        
        if os.path.exists(alternative):
            return alternative
            
        raise FileNotFoundError(f"No se encuentra el archivo de modelo: {mod_file}")
    return mod_file

def main(args):
    
    # --- ACCIÓN 1: Parseo Masivo ---
    if args.action == 'parse':
        print("--- ACCIÓN: Parsear todos los .txt a .dat ---")
        os.makedirs(DAT_DIR, exist_ok=True)
        if not os.path.exists(TXT_DIR):
            print(f"Error: No existe el directorio {TXT_DIR}")
            return

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

    # Validación de argumentos para optimal/heuristic
    if not args.instance:
        print("Error: Las acciones 'optimal' y 'heuristic' requieren el argumento -i/--instance.")
        return

    print(f"--- ACCIÓN: {args.action.upper()} | INSTANCIA: {args.instance} | MODO: {args.mode} ---")

    # Preparación de archivos
    os.makedirs(DAT_DIR, exist_ok=True)
    dat_file = os.path.join(DAT_DIR, f"{args.instance}.dat")
    
    # Si falta el .dat, intentar crearlo al vuelo
    if not os.path.exists(dat_file):
        print(f"[Main] {dat_file} no existe. Buscando .txt para convertir...")
        txt_file = os.path.join(TXT_DIR, f"{args.instance}.txt")
        if os.path.exists(txt_file):
            parse_and_convert(txt_file, dat_file)
        else:
            print(f"Error Fatal: No se encuentra ni {dat_file} ni {txt_file}")
            return
    
    try:
        mod_file = get_model_path(args.mode)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # --- ACCIÓN 2: Resolver Óptimo Real (Exacto) ---
    if args.action == 'optimal':
        print("\n[Main] Resolviendo Óptimo con Gurobi (Branch & Bound completo)...")

        optimal_cost, opt_facilities, opt_assignments = ampl_solver.solve_optimal(
            dat_file, mod_file, args.mode, solver="gurobi", timelimit=None, mipgap=0.0
        )
        
        # 1. Guardar reporte Excel
        utils.update_report_excel(
            report_path=REPORT_PATH,
            instance_name=args.instance,
            mode=args.mode,
            optimal_cost=optimal_cost
        )

        # 2. Guardar archivo de solución detallada
        if optimal_cost is not None:
            os.makedirs(SOLUTIONS_DIR, exist_ok=True)
            utils.save_solution_to_file(
                sol_dir=SOLUTIONS_DIR,
                instance_name=f"{args.instance}_OPTIMAL", # Diferenciar nombre
                mode=args.mode,
                cost=optimal_cost,
                open_facilities=opt_facilities,
                assignments=opt_assignments
            )
        
        print("--- Acción 'optimal' Finalizada ---")

    # --- ACCIÓN 3: Resolver Heurística Híbrida ---
    elif args.action == 'heuristic':
        print("\n[Main] Ejecutando Heurística Tabu Search + AMPL...")
        
        # CONFIGURACIÓN CRÍTICA PARA VELOCIDAD:
        # outlev=0: Sin ruido en consola (acelera I/O).
        # timelimit=0.5: Si SS se complica, cortar rápido (0.5 segundos).
        # mipgap=0.01: 1% de gap es suficiente para evaluar vecinos.
        gurobi_opts_fast = 'outlev=0 timelimit=0.5 mipgap=0.01' 

        try:
            # 1. Inicializar Wrapper
            ampl_wrapper = ampl_solver.AMPLWrapper(
                dat_file, 
                mod_file, 
                solver="gurobi", 
                gurobi_opts=gurobi_opts_fast
            )
        except Exception as e:
            print(f"[Main] Error iniciando AMPLWrapper: {e}")
            return
        
        print(f"[Main] Instancia cargada. {ampl_wrapper.get_n_locations()} localizaciones detectadas.")

        # 2. Ejecutar Tabu Search
        heuristic_cost, best_facilities, iters_done = heuristic.run_tabu_search(
            ampl_wrapper=ampl_wrapper,
            dat_file=dat_file, # (Legacy, no se usa dentro pero se pasa por compatibilidad)
            mod_file=mod_file, # (Legacy)
            n_locations=ampl_wrapper.get_n_locations(),
            max_iterations=args.iterations,
            tabu_tenure=args.tenure,
            neighborhood_sample_size=args.sample
        )
        
        print(f"[Main] Heurística finalizada. Mejor costo estimado: {heuristic_cost}")

        # 3. Obtener solución final detallada (Refinamiento)
        # Ahora que sabemos cuáles son los mejores centros, le damos a Gurobi
        # más tiempo y precisión (gap 0) para encontrar la mejor asignación posible para ESOS centros.
        if heuristic_cost != float('inf'):
            print("[Main] Recalculando asignación final con alta precisión...")
            
            # Cambiamos opciones a modo "Preciso"
            ampl_wrapper.ampl.setOption('gurobi_options', 'outlev=0 timelimit=10.0 mipgap=0.0')
            
            final_cost, best_assignments = ampl_wrapper.get_final_solution(best_facilities, args.mode)
            
            # Usamos el costo final recalculado (puede variar ligeramente si el gap anterior era 1%)
            if final_cost != float('inf'):
                heuristic_cost = final_cost 
        else:
            best_assignments = []

        # 4. Cerrar AMPL
        ampl_wrapper.close()
        
        # 5. Guardar Archivos
        os.makedirs(SOLUTIONS_DIR, exist_ok=True)
        
        # Archivo .txt
        utils.save_solution_to_file(
            sol_dir=SOLUTIONS_DIR, 
            instance_name=args.instance, 
            mode=args.mode, 
            cost=heuristic_cost, 
            open_facilities=best_facilities, 
            assignments=best_assignments
        )
        
        # Excel
        utils.update_report_excel(
            report_path=REPORT_PATH,
            instance_name=args.instance,
            mode=args.mode,
            heuristic_cost=heuristic_cost,
            iterations=iters_done
        )
        print("--- Acción 'heuristic' Finalizada ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resolver CFLP con Heurística Híbrida.")
    
    parser.add_argument("-a", "--action", type=str, required=True, 
                        choices=["parse", "optimal", "heuristic"], 
                        help="Acción a realizar: parsear datos, buscar óptimo exacto o ejecutar heurística.")
    
    parser.add_argument("-i", "--instance", type=str, 
                        help="Nombre de la instancia (ej: 2000x2000_1). No incluir extensión.")
    
    parser.add_argument("-m", "--mode", type=str, default="SS", 
                        choices=["SS", "MS"], 
                        help="Modo: Single-Source (SS) o Multi-Source (MS). Default: SS")
    
    # Parámetros Heurística
    parser.add_argument("-n", "--iterations", type=int, default=100, 
                        help="Número de iteraciones para la heurística. Default: 100")
    
    parser.add_argument("-t", "--tenure", type=int, default=20, 
                        help="Tenencia Tabú (cuántas iteraciones un movimiento está prohibido). Default: 20")
    
    parser.add_argument("-s", "--sample", type=int, default=100, 
                        help="Tamaño de muestra del vecindario por iteración (reduce tiempo de cómputo). Default: 100")

    args = parser.parse_args()
    
    main(args)