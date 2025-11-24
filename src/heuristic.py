import random
import time
from collections import deque

def generate_initial_solution(n_locs, total_demand, capacities):
    """Greedy constructivo para iniciar con algo decente."""
    sorted_caps = sorted(capacities.items(), key=lambda x: x[1], reverse=True)
    current_cap = 0
    open_indices = set()
    
    # Cubrir demanda + buffer
    target_demand = total_demand * 1.15 # Buffer del 15%
    
    for loc, cap in sorted_caps:
        if current_cap < target_demand:
            open_indices.add(loc)
            current_cap += cap
        else:
            break
            
    # Aleatoriedad inicial
    open_list = list(open_indices)
    if len(open_list) > 2:
        num_swap = max(1, int(len(open_list) * 0.3)) # 30% de aleatoriedad
        random.shuffle(open_list)
        to_remove = open_list[:num_swap]
        
        for rem in to_remove:
            open_indices.remove(rem)
            current_cap -= capacities[rem]
            
    # Rellenar
    all_locs = list(capacities.keys())
    random.shuffle(all_locs)
    for loc in all_locs:
        if current_cap >= target_demand:
            break
        if loc not in open_indices:
            open_indices.add(loc)
            current_cap += capacities[loc]
            
    return open_indices

def perturb_solution(current_sol, all_locs_set, strength=3):
    """Mecanismo de escape."""
    new_sol = current_sol.copy()
    current_list = list(new_sol)
    closed_list = list(all_locs_set - new_sol)
    
    # 1. Cerrar aleatorios
    if len(current_list) >= strength:
        to_close = random.sample(current_list, strength)
        for loc in to_close:
            new_sol.remove(loc)
    
    # 2. Abrir aleatorios
    if len(closed_list) >= strength:
        to_open = random.sample(closed_list, strength)
        for loc in to_open:
            new_sol.add(loc)
            
    return new_sol

def run_tabu_search(ampl_wrapper, max_iter, tenure, sample_size):
    start_time = time.time()
    n_locs = ampl_wrapper.n_locations
    all_locs_set = set(range(1, n_locs + 1))
    
    # Esto nos da el valor de referencia para calcular el porcentaje
    lower_bound = ampl_wrapper.calculate_relaxed_lower_bound()
    if lower_bound <= 0: lower_bound = 0.0001 # Protección
    
    # 1. Solución Inicial
    print("[Heuristic] Generando solución inicial...")
    current_sol = generate_initial_solution(n_locs, ampl_wrapper.total_demand, ampl_wrapper.capacities)
    
    current_cost = ampl_wrapper.solve_subproblem(current_sol)
    
    # Manejo de infactibilidad inicial
    if current_cost == float('inf'):
        print("[Heuristic] Solución inicial infactible. Abriendo más centros...")
        closed = list(all_locs_set - current_sol)
        random.shuffle(closed)
        to_add = closed[:int(len(closed)*0.2)]
        for loc in to_add:
            current_sol.add(loc)
        current_cost = ampl_wrapper.solve_subproblem(current_sol)

    best_sol = current_sol.copy()
    best_cost = current_cost
    
    # Calcular Gap Inicial
    initial_gap = ((best_cost - lower_bound) / lower_bound) * 100
    print(f"[Heuristic] Costo Inicial: {current_cost:,.2f} | GAP: {initial_gap:.2f}% (Distancia al óptimo teórico)")
    
    tabu_list = deque(maxlen=tenure)
    tabu_set = set()
    
    no_improve_iter = 0
    max_stagnation = 15 
    
    for it in range(max_iter):
        current_open_list = list(current_sol)
        current_closed_list = list(all_locs_set - current_sol)
        
        current_sample_size = sample_size
        if no_improve_iter > 5:
            current_sample_size = int(sample_size * 1.5)

        best_neighbor_cost = float('inf')
        best_neighbor_sol = None
        best_move = None 
        
        actual_sample = min(current_sample_size, len(current_open_list) * len(current_closed_list))
        
        for _ in range(actual_sample):
            u = random.choice(current_closed_list) 
            v = random.choice(current_open_list)   
            
            is_tabu = (u in tabu_set) or (v in tabu_set)
            
            neighbor = current_sol.copy()
            neighbor.add(u)
            neighbor.remove(v)
            
            cost = ampl_wrapper.solve_subproblem(neighbor)
            
            if is_tabu and cost < best_cost:
                is_tabu = False
            
            if not is_tabu and cost < float('inf'):
                if cost < best_neighbor_cost:
                    best_neighbor_cost = cost
                    best_neighbor_sol = neighbor
                    best_move = (u, v)

        # --- Lógica de movimiento ---
        if best_neighbor_sol is not None:
            current_sol = best_neighbor_sol
            current_cost = best_neighbor_cost
            
            u, v = best_move
            tabu_list.append(u)
            tabu_list.append(v)
            tabu_set = set(tabu_list)
            
            # --- Cálculo del gap ---
            gap = ((current_cost - lower_bound) / lower_bound) * 100
            gap_str = f"{gap:.2f}%"
            
            if current_cost < best_cost:
                best_cost = current_cost
                best_sol = current_sol.copy()
                no_improve_iter = 0
                print(f"[*] Iter {it+1}: Récord -> {best_cost:,.2f} | GAP: {gap_str}")
            else:
                no_improve_iter += 1
                if (it+1) % 5 == 0:
                    print(f"    Iter {it+1}: Actual {current_cost:,.2f} | GAP: {gap_str} | Stagnation: {no_improve_iter}/{max_stagnation}")

        else:
            no_improve_iter += 2 
            print(f"[!] Iter {it+1}: Sin vecinos válidos.")

        # --- Perturbación ---
        if no_improve_iter >= max_stagnation:
            print(f"[>>>] PERTURBACIÓN ACTIVADA (Stagnation {no_improve_iter}) [<<<]")
            strength = max(3, int(len(current_sol) * 0.1))
            current_sol = perturb_solution(best_sol, all_locs_set, strength=strength)
            current_cost = ampl_wrapper.solve_subproblem(current_sol)
            
            # Mostrar gap post-perturbación
            gap = ((current_cost - lower_bound) / lower_bound) * 100
            print(f"      Reinicio en costo: {current_cost:,.2f} | GAP: {gap:.2f}%")
            
            tabu_list.clear()
            tabu_set.clear()
            no_improve_iter = 0

    total_time = time.time() - start_time
    
    final_gap = ((best_cost - lower_bound) / lower_bound) * 100
    print(f"\n[Fin] Mejor Costo: {best_cost:,.2f} | Gap Final: {final_gap:.2f}%")
    
    return best_cost, list(best_sol), total_time