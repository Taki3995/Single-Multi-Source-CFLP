"""
Implementación de la heurística Búsqueda Tabú (Tabu Search) para CFLP.
"""

import random
from collections import deque
import time

def generate_initial_solution(n_locations, total_demand, capacity_list):
    """
    Genera solución inicial factible aleatoria-codiciosa.
    """
    open_indices = set()
    current_total_capacity = 0.0
    
    shuffled_capacity = capacity_list.copy()
    random.shuffle(shuffled_capacity) # Aleatoriedad

    # Fase 1: Cubrir demanda
    for capacity, j in shuffled_capacity:
        if current_total_capacity < total_demand:
            open_indices.add(j)
            current_total_capacity += capacity
        else:
            # Fase 2: Agregar holgura aleatoria (10% prob)
            if random.random() < 0.10:
                open_indices.add(j)
                current_total_capacity += capacity

    # Fase 3: Seguridad (si aún no cubre demanda, abrir al azar)
    if current_total_capacity < total_demand:
        all_indices = list(range(1, n_locations + 1))
        random.shuffle(all_indices)
        for j in all_indices:
            if j not in open_indices:
                open_indices.add(j)
                # No sumamos capacidad exacta porque no tenemos el mapa completo aquí,
                # pero confiamos en que abrir más ayudará.
                if len(open_indices) > n_locations * 0.9: break

    return open_indices

def get_neighbors_sampled(current_open_set, n_locations, sample_size):
    """
    Generador de vecinos 1-1 swap muestreado.
    """
    all_locs = set(range(1, n_locations + 1))
    closed_indices = list(all_locs - current_open_set)
    open_indices = list(current_open_set)
    
    if not closed_indices or not open_indices:
        return

    for _ in range(sample_size):
        j_open = random.choice(open_indices)
        j_closed = random.choice(closed_indices)
        
        neighbor_set = current_open_set.copy()
        neighbor_set.remove(j_open)
        neighbor_set.add(j_closed)
        
        move = (j_open, j_closed) # (cerré, abrí)
        yield neighbor_set, move

def run_tabu_search(ampl_wrapper, dat_file, mod_file, n_locations, max_iterations, tabu_tenure, neighborhood_sample_size):
    
    start_time = time.time()
    print(f"\n[Heuristic] Iniciando Tabu Search | Iter: {max_iterations} | Tenure: {tabu_tenure}")

    tabu_list = deque(maxlen=(tabu_tenure * 2)) 
    
    # 1. Solución Inicial
    total_demand = ampl_wrapper.get_total_demand()
    capacity_list = ampl_wrapper.get_capacity_list()
    
    current_solution_set = generate_initial_solution(n_locations, total_demand, capacity_list)
    current_cost = ampl_wrapper.solve_assignment_persistent(list(current_solution_set))

    # Reintentos de solución inicial
    retries = 0
    while current_cost == float('inf') and retries < 10:
        retries += 1
        print(f"[Heuristic] Solución inicial infactible. Reintentando ({retries})...")
        current_solution_set = generate_initial_solution(n_locations, total_demand, capacity_list)
        current_cost = ampl_wrapper.solve_assignment_persistent(list(current_solution_set))

    if current_cost == float('inf'):
        print("[Heuristic] ERROR: No se pudo generar una solución inicial factible.")
        return float('inf'), [], 0

    best_solution_set = current_solution_set
    best_cost = current_cost
    
    print(f"[Heuristic] Costo Inicial: {best_cost:,.2f}")

    # 2. Bucle Principal
    iterations_run = 0
    for i in range(max_iterations):
        iterations_run += 1
        
        best_neighbor_set = None
        best_neighbor_cost = float('inf')
        best_neighbor_move = None
        
        # Variables para "Pánico" (mejor movimiento aunque sea tabú si no hay otro)
        best_tabu_neighbor_set = None
        best_tabu_neighbor_cost = float('inf')
        best_tabu_move = None

        # Evaluar vecindario
        for neighbor_set, move in get_neighbors_sampled(current_solution_set, n_locations, neighborhood_sample_size):
            
            # Check rápido de Tabú
            is_tabu = (move[0] in tabu_list or move[1] in tabu_list)
            
            # Resolver subproblema
            neighbor_cost = ampl_wrapper.solve_assignment_persistent(list(neighbor_set))
            
            if neighbor_cost == float('inf'): continue # Vecino infactible

            # Criterio de Aspiración
            aspiration = (neighbor_cost < best_cost)
            
            if (not is_tabu) or aspiration:
                # Candidato válido
                if neighbor_cost < best_neighbor_cost:
                    best_neighbor_cost = neighbor_cost
                    best_neighbor_set = neighbor_set
                    best_neighbor_move = move
            else:
                # Candidato Tabú (solo lo guardamos por si acaso no hallamos nada más)
                if neighbor_cost < best_tabu_neighbor_cost:
                    best_tabu_neighbor_cost = neighbor_cost
                    best_tabu_neighbor_set = neighbor_set
                    best_tabu_move = move

        # Selección del movimiento
        if best_neighbor_set is not None:
            # Encontramos un vecino válido no tabú (o aspirado)
            current_solution_set = best_neighbor_set
            current_cost = best_neighbor_cost
            move_to_add = best_neighbor_move
        elif best_tabu_neighbor_set is not None:
            # PÁNICO: Todos eran tabú y malos, pero nos movemos al menos malo para no estancarnos
            # print(f"[Heuristic] Alerta: Movimiento Tabú forzado en iter {i}")
            current_solution_set = best_tabu_neighbor_set
            current_cost = best_tabu_neighbor_cost
            move_to_add = best_tabu_move
        else:
            print(f"[Heuristic] Estancamiento total en iter {i}. (Todos infactibles). Reiniciando vecindario...")
            continue

        # Actualizar Lista Tabú
        tabu_list.append(move_to_add[0])
        tabu_list.append(move_to_add[1])

        # Actualizar Global
        if current_cost < best_cost:
            best_cost = current_cost
            best_solution_set = current_solution_set
            print(f"*** [Heuristic] Nuevo Óptimo: {best_cost:,.2f} (Iter {i+1}) ***")
        else:
            if i % 10 == 0: # Log menos ruidoso
                print(f"[Heuristic] Iter {i+1}. Actual: {current_cost:,.2f} | Mejor: {best_cost:,.2f}")

    total_time = time.time() - start_time
    print(f"\n[Heuristic] Fin. Mejor Costo: {best_cost:,.2f}. Tiempo: {total_time:.2f}s")
    
    return best_cost, list(best_solution_set), iterations_run