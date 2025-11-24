"""
Implementación de la heurística Búsqueda Tabú (Tabu Search)
para el problema CFLP.
"""

import random
from collections import deque
import time
import sys

def generate_initial_solution(n_locations, total_demand, capacity_list):
    """
    Genera una solución inicial aleatoria PERO FACTIBLE.
    Abre centros (priorizando los de mayor capacidad, pero con
    aleatoriedad) hasta que la capacidad total abierta cubra la demanda total.
    """
    print(f"[Heuristic] Generando sol. inicial para Demanda Total: {total_demand:,.0f}")
    
    open_indices = set()
    current_total_capacity = 0.0
    
    # Copiamos la lista y la barajamos para añadir aleatoriedad
    # Esto evita que siempre abra los mismos N centros más grandes.
    shuffled_capacity_list = capacity_list.copy()
    random.shuffle(shuffled_capacity_list)

    all_indices = set(range(1, n_locations + 1))
    opened_indices_from_list = set()

    for capacity, j in shuffled_capacity_list:
        if current_total_capacity < total_demand:
            open_indices.add(j)
            opened_indices_from_list.add(j)
            current_total_capacity += capacity
        else:
            # Una vez cubierta la demanda, opcionalmente abrimos algunos
            # pocos más para dar holgura.
            if random.random() < 0.10:
                open_indices.add(j)
                opened_indices_from_list.add(j)
                current_total_capacity += capacity

    # Asegurar que se abran centros aunque no tengan capacidad (si es necesario)
    if current_total_capacity < total_demand:
        print("[Heuristic] Advertencia: Capacidad insuficiente. Abriendo más centros al azar.")
        remaining_indices = list(all_indices - opened_indices_from_list)
        random.shuffle(remaining_indices)
        for j in remaining_indices:
            open_indices.add(j)
            # Suponemos que si no estaba en la lista, su capacidad era 0
            if len(open_indices) > (n_locations * 0.8): # No abrir más del 80%
                break

    if current_total_capacity < total_demand:
        print(f"[Heuristic] ADVERTENCIA: La suma de TODAS las capacidades ({current_total_capacity:,.0f}) podría ser menor que la demanda total.")
        
    print(f"[Heuristic] Solución inicial generada con {len(open_indices)} centros abiertos.")
    print(f"[Heuristic] Capacidad Abierta: {current_total_capacity:,.0f}")
    return open_indices


def get_neighbors_sampled(current_open_set, n_locations, sample_size):
    """
    Generador de vecinos muestreado (Sampling).
    Genera 'sample_size' vecinos aleatorios 1-1 swap.
    """
    
    closed_indices = list(set(range(1, n_locations + 1)) - current_open_set)
    open_indices = list(current_open_set)
    
    if not closed_indices or not open_indices:
        # No hay nada que intercambiar
        return

    # Genera 'sample_size' vecinos aleatorios
    for _ in range(sample_size):
        try:
            # 1. Elegir un centro abierto al azar para cerrar
            j_open = random.choice(open_indices)
            
            # 2. Elegir un centro cerrado al azar para abrir
            j_closed = random.choice(closed_indices)
            
            # 3. Crear el set vecino
            neighbor_set = current_open_set.copy()
            neighbor_set.remove(j_open)
            neighbor_set.add(j_closed)
            
            # 4. Definir el movimiento (lo que se guardará en la lista tabú)
            move = (j_open, j_closed) 
            
            yield neighbor_set, move
            
        except IndexError:
            # Ocurre si las listas están vacías, simplemente paramos
            break

def run_tabu_search(ampl_wrapper, dat_file, mod_file, n_locations, max_iterations, tabu_tenure, neighborhood_sample_size):
    """
    Función principal de Búsqueda Tabú.
    (dat_file y mod_file ya no se usan, pero se mantienen 
    en la firma para no romper la llamada de main.py)
    """
    start_time = time.time()
    
    print(f"\n[Heuristic] Iniciando Búsqueda Tabú...")
    print(f"Instancia: {n_locations} loc")
    print(f"Iteraciones Máximas: {max_iterations}")
    print(f"Tamaño Lista Tabú (Tenure): {tabu_tenure}")
    print(f"Tamaño Muestreo Vecinario: {neighborhood_sample_size}")

    # Inicialización
    tabu_list = deque(maxlen=(tabu_tenure * 2)) 
    tabu_set = set()
    
    print("[Heuristic] Buscando solución inicial factible...")
    
    # Obtener los datos para la solución inicial "inteligente"
    total_demand = ampl_wrapper.get_total_demand()
    capacity_list = ampl_wrapper.get_capacity_list()
    
    # Generar una solución inicial (factible)
    current_solution_set = generate_initial_solution(n_locations, total_demand, capacity_list)
    
    # Llamada a la función persistente (rápida)
    current_cost = ampl_wrapper.solve_assignment_persistent(list(current_solution_set))

    # Bucle de reintento si la solución es infactible (costo 'inf')
    max_retries = 5 # Bajar reintentos
    retries = 0
    while current_cost == float('inf') and retries < max_retries:
        retries += 1
        print(f"[Heuristic] Solución inicial infactible (quizás por mala suerte). Reintentando ({retries}/{max_retries})...")
        
        # Generar otra solución aleatoria (pero factible en capacidad)
        current_solution_set = generate_initial_solution(n_locations, total_demand, capacity_list)
        
        # Llamada a la función persistente (rápida)
        current_cost = ampl_wrapper.solve_assignment_persistent(list(current_solution_set))

    if current_cost == float('inf'):
        print("[Heuristic] ERROR: No se pudo encontrar una solución inicial factible después de 5 intentos.")
        print("[Heuristic] Verifica que la suma de TODAS las capacidades en el .dat sea mayor a la demanda total.")
        return float('inf'), [], 0 # Salir
    
    # Inicializar la mejor solución encontrada
    best_solution_set = current_solution_set
    best_cost = current_cost
    
    print(f"[Heuristic] Costo Inicial: {best_cost:,.2f}")

    # Bucle Principal de Búsqueda Tabú
    iterations_run = 0
    for i in range(max_iterations):
        iterations_run += 1
        best_neighbor_set = None
        best_neighbor_cost = float('inf')
        best_neighbor_move = None

        # Explorar Vecindario muestreado
        for neighbor_set, move in get_neighbors_sampled(current_solution_set, n_locations, neighborhood_sample_size):
            
            # 'move' = (j_que_cerre, j_que_abri)
            is_tabu = (move[0] in tabu_set or move[1] in tabu_set)
            
            # Evaluación del vecino (Llamada a la función persistente (rápida))
            neighbor_cost = ampl_wrapper.solve_assignment_persistent(list(neighbor_set))

            # Criterio de Aspiración:
            # Aceptamos si es mejor que la mejor solución global
            aspiration_met = (neighbor_cost < best_cost)
            
            if (not is_tabu) or aspiration_met:
                if neighbor_cost < best_neighbor_cost:
                    best_neighbor_set = neighbor_set
                    best_neighbor_cost = neighbor_cost
                    best_neighbor_move = move 

        # Mover a la mejor solución vecina encontrada
        if best_neighbor_set is None:
            print(f"[Heuristic] Iter {i+1}/{max_iterations}. No se encontraron vecinos válidos. (Posible óptimo local)")
            # (Opcional: podrías "resetear" o diversificar aquí)
            continue # Saltar esta iteración
            
        current_solution_set = best_neighbor_set
        current_cost = best_neighbor_cost
        
        # 'move' = (j_que_cerre, j_que_abri)
        j_closed = best_neighbor_move[0]
        j_opened = best_neighbor_move[1]
        
        # Añadir nuevos
        tabu_list.append(j_closed)
        tabu_list.append(j_opened)
        
        # Sincronizar
        tabu_set = set(tabu_list)

        # --- Actualizar la Mejor Solución Global ---
        if current_cost < best_cost:
            best_solution_set = current_solution_set
            best_cost = current_cost
            print(f"*** [Heuristic] Iter {i+1}/{max_iterations}. Nuevo Óptimo Encontrado! Costo: {best_cost:,.2f} ***")
        else:
            # Imprime el progreso al final de CADA iteración
            print(f"[Heuristic] Iter {i+1}/{max_iterations}. Costo actual: {current_cost:,.2f} (Mejor: {best_cost:,.2f})")

    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n[Heuristic] Búsqueda Tabú Finalizada.")
    print(f"Mejor Costo Encontrado: {best_cost:,.2f}")
    print(f"Total Centros Abiertos: {len(best_solution_set)}")
    print(f"Tiempo Total: {total_time:.2f} segundos")
    
    # Retorna la mejor solución (índices 1-based) y su costo
    return best_cost, list(best_solution_set), iterations_run