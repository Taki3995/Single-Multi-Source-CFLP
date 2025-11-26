import os
import argparse
from data_parser import parse_and_convert
import ampl_solver
import utils
import heuristic

# --- Configuración de Rutas y Directorios ---
# Define la estructura de carpetas relativa a la ubicación de este script.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TXT_DIR = os.path.join(DATA_DIR, 'instances_txt')   # Instancias originales en texto plano
DAT_DIR = os.path.join(DATA_DIR, 'instances_dat')   # Instancias convertidas para AMPL
MODELS_DIR = os.path.join(BASE_DIR, 'models')       # Archivos .mod de AMPL
SOLUTIONS_DIR = os.path.join(BASE_DIR, 'solutions') # Salida de resultados
REPORT_PATH = os.path.join(BASE_DIR, 'report.xlsx') # Reporte general en Excel

def get_model_path(mode):
    """
    Selecciona el archivo de modelo AMPL (.mod) correcto basándose en el modo:
    SS: Single Source
    MS: Multi Source
    """
    if mode == "SS":
        mod_file = os.path.join(MODELS_DIR, 'cflp_SingleSource.mod')
    elif mode == "MS":
        mod_file = os.path.join(MODELS_DIR, 'cflp_MultiSource.mod')
    else:
        raise ValueError(f"Modo '{mode}' no reconocido.")
        
    # Verificación de existencia del archivo
    if not os.path.exists(mod_file):
        # Intento de recuperación por sensibilidad a mayúsculas/minúsculas (Linux vs Windows)
        if mode == "SS": alt = os.path.join(MODELS_DIR, 'CFLP_SingleSource.mod')
        else: alt = os.path.join(MODELS_DIR, 'CFLP_MultiSource.mod')
        if os.path.exists(alt): return alt
        raise FileNotFoundError(f"No se encuentra el modelo: {mod_file}")
    return mod_file

def main(args):
    
    # --- ACCIÓN 1: Parseo (Preparación de datos) ---
    # Si se selecciona 'parse', convierte todas las instancias .txt a formato .dat de AMPL y termina.
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
                # Solo genera el archivo si no existe previamente
                if not os.path.exists(dat):
                    print(f"Generando {dat}...")
                    parse_and_convert(txt, dat)
        print("--- Parseo Completado ---")
        return

    # Validación: Para 'optimal' o 'heuristic', se requiere especificar una instancia.
    if not args.instance:
        print("Error: Requiere -i / --instance")
        return

    print(f"--- ACCIÓN: {args.action.upper()} | INSTANCIA: {args.instance} | MODO: {args.mode} ---")

    # Asegurar que el archivo .dat específico de la instancia exista
    os.makedirs(DAT_DIR, exist_ok=True)
    dat_file = os.path.join(DAT_DIR, f"{args.instance}.dat")
    
    # Generación dinámica del .dat si falta
    if not os.path.exists(dat_file):
        print(f"[Main] Creando {dat_file}...")
        txt_file = os.path.join(TXT_DIR, f"{args.instance}.txt")
        if os.path.exists(txt_file):
            parse_and_convert(txt_file, dat_file)
        else:
            print(f"Error Fatal: No existe la instancia fuente {txt_file}")
            return
    
    # Obtener la ruta del modelo AMPL adecuado
    try: mod_file = get_model_path(args.mode)
    except Exception as e: print(e); return

    # Acción PLot: Ejecuta optimal -> heurístic -> Plot
    if args.action == 'plot':
        print("\n=== FASE 1: Calculando Óptimo Real (AMPL Puro) ===")
        # 1. Resolver Óptimo
        opt_cost, _, _ = ampl_solver.solve_optimal(
            dat_file, mod_file, args.mode, solver="gurobi", timelimit=None, mipgap=0.0
        )
        print(f"--> Costo Óptimo obtenido: {opt_cost}")
        
        # Guardar en reporte
        utils.update_report_excel(REPORT_PATH, args.instance, args.mode, optimal_cost=opt_cost)

        print("\n=== FASE 2: Ejecutando Heurística (AMPL + Python) ===")
        # 2. Ejecutar Heurística
        gurobi_opts = 'outlev=0 timelimit=5.0 mipgap=0.05' 
        try:
            wrapper = ampl_solver.AMPLWrapper(dat_file, mod_file, solver="gurobi", gurobi_opts=gurobi_opts)
            heu_cost, best_facilities, iters_done, history = heuristic.run_tabu_search(
                wrapper, dat_file, mod_file, wrapper.get_n_locations(),
                args.iterations, args.tenure, args.sample
            )
            
            # Refinamiento final (para guardar el dato correcto en excel)
            if heu_cost != float('inf'):
                print("[Main] Refinando asignación final...")
                wrapper.ampl.setOption('gurobi_options', 'outlev=0 timelimit=10.0 mipgap=0.0')
                final_c, final_assigns = wrapper.get_final_solution(best_facilities, args.mode)
                if final_c != float('inf'): heu_cost = final_c
            else:
                final_assigns = []
            
            wrapper.close()

            # Guardar Solución y Reporte
            os.makedirs(SOLUTIONS_DIR, exist_ok=True)
            utils.save_solution_to_file(SOLUTIONS_DIR, args.instance, args.mode, heu_cost, best_facilities, final_assigns)
            utils.update_report_excel(REPORT_PATH, args.instance, args.mode, heuristic_cost=heu_cost, iterations=iters_done)

        except Exception as e:
            print(f"[Main] Error en la fase heurística: {e}")
            return

        print("\n=== FASE 3: Generando Gráfico Comparativo ===")
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 6))
            
            # A. Graficar curva de convergencia de la heurística
            plt.plot(range(len(history)), history, marker='o', markersize=3, linestyle='-', color='#1f77b4', label='Heurística (Tabu)')
            
            # B. Graficar línea horizontal del óptimo (Si existe)
            if opt_cost is not None:
                plt.axhline(y=opt_cost, color='r', linestyle='--', linewidth=2, label=f'Óptimo Real ({opt_cost:,.0f})')
                
                # Calcular GAP final para ponerlo en el título
                if heu_cost != float('inf'):
                    gap = ((heu_cost - opt_cost) / opt_cost) * 100
                    title_extra = f" | GAP Final: {gap:.2f}%"
                else:
                    title_extra = ""
            else:
                title_extra = ""

            plt.title(f'Convergencia: {args.instance} ({args.mode}){title_extra}', fontsize=12)
            plt.xlabel('Iteraciones')
            plt.ylabel('Costo Total')
            plt.legend()
            plt.grid(True, alpha=0.5)
            
            # Guardar
            img_path = os.path.join(SOLUTIONS_DIR, f"comparison_{args.instance}_{args.mode}.png")
            plt.savefig(img_path, dpi=120)
            plt.close()
            print(f"[Main] ¡Gráfico generado exitosamente en: {img_path}!")

        except ImportError:
            print("[Main] Error: No tienes matplotlib instalado.")
        except Exception as e:
            print(f"[Main] Error generando gráfico: {e}")
        
        return

    # --- ACCIÓN 2: Resolución Exacta (Benchmark) ---
    # Utiliza Gurobi directamente sobre el modelo completo para encontrar el óptimo matemático.
    if args.action == 'optimal':
        print("\n[Main] Resolviendo Óptimo con Gurobi...")
        # mipgap=0.0 fuerza a buscar el óptimo exacto sin margen de error.
        optimal_cost, opt_facilities, opt_assignments = ampl_solver.solve_optimal(
            dat_file, mod_file, args.mode, solver="gurobi", timelimit=None, mipgap=0.0
        )
        
        # Guardar en Excel y archivo de texto
        utils.update_report_excel(REPORT_PATH, args.instance, args.mode, optimal_cost=optimal_cost)
        
        if optimal_cost is not None:
            os.makedirs(SOLUTIONS_DIR, exist_ok=True)
            utils.save_solution_to_file(SOLUTIONS_DIR, f"{args.instance}_OPTIMAL", args.mode, optimal_cost, opt_facilities, opt_assignments)
        print("--- Fin Optimal ---")

    # --- ACCIÓN 3: Metaheurística (Tabu Search) ---
    elif args.action == 'heuristic':
        print("\n[Main] Ejecutando Heurística Tabu Search...")
        
        # Configuración de Gurobi para la fase de búsqueda (Exploración):
        # outlev=0: Silencia el output de la consola.
        # timelimit=5.0: Límite de tiempo por sub-problema (evaluación de vecinos) para no bloquearse.
        # mipgap=0.05: Acepta soluciones al 5% del óptimo durante la búsqueda para ganar velocidad.
        gurobi_opts_heuristic = 'outlev=0 timelimit=5.0 mipgap=0.05' 

        try:
            # Inicializa el wrapper de AMPL con la configuración rápida
            ampl_wrapper = ampl_solver.AMPLWrapper(dat_file, mod_file, solver="gurobi", gurobi_opts=gurobi_opts_heuristic)
        except Exception as e:
            print(f"[Main] Error iniciando AMPL: {e}")
            return
        
        print(f"[Main] Instancia cargada. Locs: {ampl_wrapper.get_n_locations()}")

        # Ejecuta el algoritmo Tabu Search
        # Desempaquetamos la nueva variable 'history'
        heuristic_cost, best_facilities, iters_done, history = heuristic.run_tabu_search(
            ampl_wrapper, dat_file, mod_file, ampl_wrapper.get_n_locations(),
            args.iterations, args.tenure, args.sample
        )
        
        print(f"[Main] Heurística fin. Mejor costo est.: {heuristic_cost}")

        # --- Fase de Refinamiento (Explotación final) ---
        # Una vez que la heurística decidió QUÉ instalaciones abrir, resolvemos la asignación exacta
        # con mayor precisión (mipgap=0.0) y más tiempo, para asegurar el costo real mínimo.
        if heuristic_cost != float('inf'):
            print("[Main] Refinando asignación final...")
            ampl_wrapper.ampl.setOption('gurobi_options', 'outlev=0 timelimit=20.0 mipgap=0.0')
            final_cost, best_assignments = ampl_wrapper.get_final_solution(best_facilities, args.mode)
            if final_cost != float('inf'): heuristic_cost = final_cost 
        else:
            best_assignments = []

        ampl_wrapper.close()
        
        # Guardado de resultados
        os.makedirs(SOLUTIONS_DIR, exist_ok=True)
        utils.save_solution_to_file(SOLUTIONS_DIR, args.instance, args.mode, heuristic_cost, best_facilities, best_assignments)
        
        utils.update_report_excel(REPORT_PATH, args.instance, args.mode, heuristic_cost=heuristic_cost, iterations=iters_done)
        print("--- Fin Heurística ---")

if __name__ == "__main__":
    # Configuración de argumentos de línea de comandos
    parser = argparse.ArgumentParser()
    # -a: Acción a realizar (parsear datos, resolver óptimo o correr heurística)
    parser.add_argument("-a", "--action", required=True, choices=["parse", "optimal", "heuristic", "plot"])
    # -i: Nombre de la instancia (ej: p1, cap41, etc.)
    parser.add_argument("-i", "--instance", type=str)
    # -m: Modo del problema (SS: Single Source, MS: Multi Source)
    parser.add_argument("-m", "--mode", type=str, default="SS", choices=["SS", "MS"])
    # Parámetros de la heurística Tabu Search
    parser.add_argument("-n", "--iterations", type=int, default=100) # Número máximo de iteraciones
    parser.add_argument("-t", "--tenure", type=int, default=20)      # Tamaño de la lista tabú
    parser.add_argument("-s", "--sample", type=int, default=100)     # % de vecindario a explorar
    args = parser.parse_args()
    main(args)