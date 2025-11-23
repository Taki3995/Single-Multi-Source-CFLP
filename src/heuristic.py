import random
import time
from collections import deque

def generate_initial_solution(n_locs, total_demand, capacities):
    """Greedy constructivo para iniciar con algo decente."""
    # Ordenar centros por capacidad descendente
    sorted_caps = sorted(capacities.items(), key=lambda x: x[1], reverse=True)
    
    current_cap = 0
    open_indices = set()
    
    # Seleccionar centros hasta cubrir demanda + un buffer del 10%
    target_demand = total_demand * 1.1
    
    for loc, cap in sorted_caps:
        if current_cap < target_demand:
            open_indices.add(loc)
            current_cap += cap
        else:
            break
            
    # Cerrar algunos de los elegidos para dar variedad.
    open_list = list(open_indices)
    if len(open_list) > 2:
        # Calculamos cuántos quitar
        num_swap = max(1, int(len(open_list) * 0.2))
        
        # Mezclamos la lista para elegir 'num_swap' elementos ÚNICOS al azar
        random.shuffle(open_list)
        
        # Tomamos los primeros 'num_swap' elementos para eliminar
        to_remove = open_list[:num_swap]
        
        for rem in to_remove:
            open_indices.remove(rem)
            current_cap -= capacities[rem]
            
    # Rellenar aleatoriamente si bajamos de la demanda tras eliminar
    all_locs = list(capacities.keys())
    random.shuffle(all_locs)
    
    for loc in all_locs:
        if current_cap >= target_demand:
            break
        if loc not in open_indices:
            open_indices.add(loc)
            current_cap += capacities[loc]
            
    return open_indices

def run_tabu_search(ampl_wrapper, max_iter, tenure, sample_size):
    start_time = time.time()
    n_locs = ampl_wrapper.n_locations
    
    # 1. Solución Inicial
    print("[Heuristic] Generando solución inicial...")
    current_sol = generate_initial_solution(n_locs, ampl_wrapper.total_demand, ampl_wrapper.capacities)
    
    # Evaluar
    current_cost = ampl_wrapper.solve_subproblem(current_sol)
    
    # Manejo de infactibilidad inicial
    if current_cost == float('inf'):
        print("[Heuristic] Solución inicial infactible. Intentando abrir todo...")
        current_sol = set(range(1, n_locs + 1))
        current_cost = ampl_wrapper.solve_subproblem(current_sol)
    
    best_sol = current_sol.copy()
    best_cost = current_cost
    
    print(f"[Heuristic] Costo Inicial: {current_cost:,.2f}")
    
    # Estructuras Tabú
    tabu_list = deque(maxlen=tenure)
    tabu_set = set() 
    
    all_locs = set(range(1, n_locs + 1))
    
    # Loop
    no_improve_iter = 0
    
    for it in range(max_iter):
        current_open_list = list(current_sol)
        current_closed_list = list(all_locs - current_sol)
        
        if not current_open_list or not current_closed_list:
            break

        # Muestreo
        num_samples = min(sample_size, len(current_open_list) * len(current_closed_list))
        
        best_neighbor_cost = float('inf')
        best_neighbor_sol = None
        best_move = None #(in, out)
        
        # Iterar muestras
        for _ in range(num_samples):
            u = random.choice(current_closed_list) # Abrir
            v = random.choice(current_open_list)   # Cerrar
            
            # Verificar Tabú
            is_tabu = (u in tabu_set) or (v in tabu_set)
            
            # Crear vecino (Set copy es rápido en Python)
            neighbor = current_sol.copy()
            neighbor.add(u)
            neighbor.remove(v)
            
            # Evaluar
            cost = ampl_wrapper.solve_subproblem(neighbor)
            
            # Criterio de Aspiración
            if is_tabu and cost < best_cost:
                is_tabu = False 
            
            if not is_tabu and cost < float('inf'):
                if cost < best_neighbor_cost:
                    best_neighbor_cost = cost
                    best_neighbor_sol = neighbor
                    best_move = (u, v)

        # Movimiento
        if best_neighbor_sol is not None:
            current_sol = best_neighbor_sol
            current_cost = best_neighbor_cost
            
            # Actualizar Tabú
            u, v = best_move
            tabu_list.append(u)
            tabu_list.append(v)
            tabu_set = set(tabu_list) # Sincronizar set
            
            if current_cost < best_cost:
                best_cost = current_cost
                best_sol = current_sol.copy()
                no_improve_iter = 0
                print(f"[*] Iter {it+1}: Nuevo Récord -> {best_cost:,.2f}")
            else:
                no_improve_iter += 1
                if (it+1) % 10 == 0:
                    print(f"    Iter {it+1}: Actual {current_cost:,.2f} (Mejor: {best_cost:,.2f})")
        else:
            # Si no hay vecinos válidos, pasamos turno
            pass
            
    total_time = time.time() - start_time
    return best_cost, list(best_sol), total_time