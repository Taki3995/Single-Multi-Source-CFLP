"""
Implementación de la heurística Búsqueda Tabú (Tabu Search)
para el problema CFLP.
"""

import random
from collections import deque
import time

def generate_initial_solution(n_locations, open_ratio=0.2):
    """
    Genera una solución inicial aleatoria.
    Abre un 'open_ratio' (20%) de centros.
    Retorna un set de índices (1-based) de centros abiertos.
    """
    k = max(5, int(n_locations * open_ratio)) 
    all_indices = list(range(1, n_locations + 1))
    open_indices = set(random.sample(all_indices, k))
    
    print(f"[Heuristic] Solución inicial generada con {k} centros abiertos.")
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


def run_tabu_search(ampl_wrapper, n_locations, max_iterations, tabu_tenure_percent=0.10, neighborhood_sample_size=500):
    """
    Función principal de Búsqueda Tabú.
    Recibe el 'ampl_wrapper' (que ya tiene los datos cargados)
    y el 'n_locations' (detectado por el wrapper).
    """
    start_time = time.time()

    # Definir el tamaño de la lista tabú
    tabu_tenure = max(5, int(n_locations * tabu_tenure_percent))
    
    print(f"\n[Heuristic] Iniciando Búsqueda Tabú...")
    print(f"Instancia: {n_locations} loc")
    print(f"Iteraciones Máximas: {max_iterations}")
    print(f"Tamaño Lista Tabú (Tenure): {tabu_tenure}")
    print(f"Tamaño Muestreo Vecindario: {neighborhood_sample_size}")

    # Inicialización
    tabu_list = deque(maxlen=tabu_tenure) 
    tabu_set = set()
    
    # Solución Inicial
    current_solution_set = generate_initial_solution(n_locations)
    
    # Evaluación Inicial
    print("[Heuristic] Evaluando solución inicial...")
    current_cost = ampl_wrapper.solve_assignment_fixed_x(list(current_solution_set))
    
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
        
        # Explorar Vecindario MUESTRADO (Rápido)
        for neighbor_set, move in get_neighbors_sampled(current_solution_set, n_locations, neighborhood_sample_size):
            
            # 'move' = (j_que_cerre, j_que_abri)
            is_tabu = (move[0] in tabu_set or move[1] in tabu_set)
            
            # Evaluación del vecino
            neighbor_cost = ampl_wrapper.solve_assignment_fixed_x(list(neighbor_set))

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
        
        # Sincronizar (eliminar el más antiguo si la lista está llena)
        if len(tabu_list) >= tabu_tenure:
            tabu_set = set(tabu_list)

        # --- Actualizar la Mejor Solución Global ---
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
    return best_cost, list(best_solution_set), iterations_run