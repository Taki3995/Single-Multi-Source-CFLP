"""
Implementación de la heurística Búsqueda Tabú (Tabu Search)
La heurística se encarga de buscar el "vector de centros abiertos" (solución x)
y utiliza AMPL para evaluar el costo de asignación (solución y) de ese vector.
"""

import random
from collections import deque
import ampl_solver
import time

def get_instance_dims(dat_file_path):
    """
    Leer n_locations y n_clients del .dat
    """
    loc = 0
    cli = 0
    try:
        with open(dat_file_path, 'r') as f:
            for line in f:
                if line.strip().startswith("param loc :="):
                    loc = int(line.split(":=")[1].strip().replace(";", ""))
                if line.strip().startswith("param cli :="):
                    cli = int(line.split(":=")[1].strip().replace(";", ""))
                if loc > 0 and cli > 0:
                    break
        return loc, cli
    except Exception as e:
        print(f"[Heuristic] Error leyendo dimensiones del .dat: {e}")
        return 0, 0


def generate_initial_solution(n_locations, n_clients):
    """
    Genera una solución inicial aleatoria.
    Abre un número 'k' aleatorio de centros.
    Retorna un set de índices (1-based) de centros abiertos.
    """
    # k = Número de centros a abrir
    k = max(5, int(n_locations * 0.2)) 
    
    # Genera una lista de todos los índices posibles (1 a n_locations)
    all_indices = list(range(1, n_locations + 1))
    
    # Elige k índices al azar
    open_indices = set(random.sample(all_indices, k))
    
    print(f"[Heuristic] Solución inicial generada con {k} centros abiertos.")
    return open_indices

def get_neighbors(current_open_set, n_locations, move_type="1-1-swap"):
    """
    Generador de vecinos.
    Un vecino se crea por un "movimiento".
    
    Movimiento "1-1-swap": Cierra un centro abierto y abre uno cerrado.
    Retorna: (set_vecino, movimiento)
    El 'movimiento' es lo que se guarda en la lista tabú.
    """
    
    # Índices de centros cerrados
    closed_indices = set(range(1, n_locations + 1)) - current_open_set
    
    # Generar todos los swaps 1-1
    for j_open in current_open_set:
        for j_closed in closed_indices: # Por cada j_open que se cierra, se abre un j_closed
            
            # 1. Crear el set vecino
            neighbor_set = current_open_set.copy()
            neighbor_set.remove(j_open)
            neighbor_set.add(j_closed)
            
            # 2. Definir el movimiento
            move = (j_open, j_closed) 
            
            yield neighbor_set, move


def run_tabu_search(dat_file, mod_file, max_iterations, tabu_tenure_percent=0.10):
    start_time = time.time()

    # Obtener dimensiones
    n_locations, n_clients = get_instance_dims(dat_file)
    if n_locations == 0:
        return float('inf'), [], 0

    # Definir el tamaño de la lista tabú
    tabu_tenure = max(5, int(n_locations * tabu_tenure_percent))
    
    print(f"\n[Heuristic] Iniciando Búsqueda Tabú...")
    print(f"Instancia: {n_locations} loc x {n_clients} cli")
    print(f"Iteraciones Máximas: {max_iterations}")
    print(f"Tamaño Lista Tabú (Tenure): {tabu_tenure}")

    # Inicialización
    tabu_list = deque(maxlen=tabu_tenure) # Eficiencia FIFO
    
    # Solución Inicial
    current_solution_set = generate_initial_solution(n_locations, n_clients)
    
    # Evaluación Inicial (Primera llamada a AMPL)
    print("[Heuristic] Evaluando solución inicial con AMPL...")
    current_cost = ampl_solver.solve_assignment(
        dat_file, mod_file, list(current_solution_set)
    )
    
    # Inicializar la mejor solución encontrada
    best_solution_set = current_solution_set
    best_cost = current_cost
    
    print(f"[Heuristic] Costo Inicial: {best_cost:,.2f}")

    # Bucle Principal de Búsqueda Tabú
    for i in range(max_iterations):
        
        best_neighbor_set = None
        best_neighbor_cost = float('inf')
        best_neighbor_move = None
        
        # Explorar Vecindario (1-1 Swaps)
        # (Esto puede ser lento para N grande, se podría muestrear)
        neighbors_evaluated = 0
        for neighbor_set, move in get_neighbors(current_solution_set, n_locations):
            
            # Comprobar Lista Tabú y Criterio de Aspiración
            
            # 'move' = (j_que_cerre, j_que_abri)
            # 'rev_move' = (j_que_abri, j_que_cerre)
            # Verificamos si el índice que *cambió* está tabú.
            # Movimiento simple: prohibir mover 'j_open' o 'j_closed'
            is_tabu = (move[0] in tabu_list or move[1] in tabu_list)
            
            # Evaluación del vecino (Llamada a AMPL)
            neighbor_cost = ampl_solver.solve_assignment(
                dat_file, mod_file, list(neighbor_set)
            )
            neighbors_evaluated += 1

            # Criterio de Aspiración:
            # Si el vecino es mejor que la *mejor solución global encontrada hasta ahora, lo aceptamos aunque sea Tabú.
            aspiration_met = (neighbor_cost < best_cost)
            
            if (not is_tabu) or aspiration_met:
                # Si este vecino es el mejor *de este vecindario*
                if neighbor_cost < best_neighbor_cost:
                    best_neighbor_set = neighbor_set
                    best_neighbor_cost = neighbor_cost
                    # El movimiento es (j_que_cerre, j_que_abri)
                    best_neighbor_move = move 
            
            # (Opcional) Cortar la búsqueda de vecinos si es muy grande
            # if neighbors_evaluated > 200: 
            #     break

        # Mover a la mejor solución vecina encontrada
        if best_neighbor_set is None:
            print(f"[Heuristic] Iter {i+1}/{max_iterations}. No se encontraron vecinos no-tabú. Terminando.")
            break
            
        current_solution_set = best_neighbor_set
        current_cost = best_neighbor_cost
        
        # Actualizar Lista Tabú
        # Añadimos los índices que acabamos de mover
        tabu_list.append(best_neighbor_move[0]) # j que cerré
        tabu_list.append(best_neighbor_move[1]) # j que abrí

        # Actualizar la Mejor Solución Global (Best-So-Far)
        if current_cost < best_cost:
            best_solution_set = current_solution_set
            best_cost = current_cost
            print(f"*** [Heuristic] Iter {i+1}/{max_iterations}. Nuevo Óptimo Encontrado! Costo: {best_cost:,.2f} ***")
        else:
            if (i+1) % 10 == 0: # Imprimir progreso cada 10 iter.
                print(f"[Heuristic] Iter {i+1}/{max_iterations}. Costo actual: {current_cost:,.2f} (Mejor: {best_cost:,.2f})")

    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n[Heuristic] Búsqueda Tabú Finalizada.")
    print(f"Mejor Costo Encontrado: {best_cost:,.2f}")
    print(f"Total Centros Abiertos: {len(best_solution_set)}")
    print(f"Tiempo Total: {total_time:.2f} segundos")
    
    # Retorna la mejor solución (índices 1-based) y su costo
    return best_cost, list(best_solution_set), (i+1)