"""
Implementación de la heurística Búsqueda Tabú (Tabu Search) para CFLP.
Esta heurística divide el problema en dos partes:
1. Maestro (Python): Decide qué instalaciones abrir (vector x).
2. Esclavo (AMPL/Gurobi): Dado 'x', decide la asignación óptima de clientes (vector y) y devuelve el costo.
"""

import random
from collections import deque
import time

def generate_initial_solution(n_locations, total_demand, capacity_list):
    """
    Genera una solución inicial factible utilizando una estrategia Constructiva Aleatoria-Codiciosa.
    Se asegura de abrir suficientes centros para cubrir la demanda total.
    """
    open_indices = set()
    current_total_capacity = 0.0
    
    # Crea una copia de las capacidades y las mezcla para diversificar el punto de partida
    shuffled_capacity = capacity_list.copy()
    random.shuffle(shuffled_capacity) # Factor de aleatoriedad para no empezar siempre igual

    # Fase 1: Cobertura Greedy
    # Abre instalaciones una por una hasta que la capacidad acumulada supere la demanda.
    for capacity, j in shuffled_capacity:
        if current_total_capacity < total_demand:
            open_indices.add(j)
            current_total_capacity += capacity
        else:
            # Fase 2: Holgura Probabilística
            # Una vez cubierta la demanda, agrega instalaciones extra con un 10% de probabilidad.
            # Esto ayuda a evitar soluciones iniciales demasiado "ajustadas" que podrían ser infactibles.
            if random.random() < 0.10:
                open_indices.add(j)
                current_total_capacity += capacity

    # Fase 3: Red de Seguridad (Safety Net)
    # Si por alguna razón aleatoria no se cubrió la demanda (raro, pero posible), forzamos abrir más.
    if current_total_capacity < total_demand:
        all_indices = list(range(1, n_locations + 1))
        random.shuffle(all_indices)
        for j in all_indices:
            if j not in open_indices:
                open_indices.add(j)
                # No actualizamos current_total_capacity exacto aquí, 
                # simplemente abrimos hasta el 90% de las instalaciones como medida desesperada.
                if len(open_indices) > n_locations * 0.9: break

    return open_indices

def get_neighbors_sampled(current_open_set, n_locations, sample_size):
    """
    Generador de vecinos utilizando el movimiento 'SWAP' (Intercambio 1-1).
    Estrategia: Cierra un centro abierto y abre uno cerrado.
    
    Para instancias grandes, evaluar todos los vecinos (N * M) es muy lento.
    Usamos sampling para evaluar solo un subconjunto aleatorio.
    """
    all_locs = set(range(1, n_locations + 1))
    
    # Identificar candidatos para cerrar (actualmente abiertos) y para abrir (actualmente cerrados)
    closed_indices = list(all_locs - current_open_set)
    open_indices = list(current_open_set)
    
    # Si no hay margen de movimiento, no genera nada
    if not closed_indices or not open_indices:
        return

    # Genera 'sample_size' vecinos aleatorios
    for _ in range(sample_size):
        j_open = random.choice(open_indices)   # Candidato a cerrar
        j_closed = random.choice(closed_indices) # Candidato a abrir
        
        # Construye el nuevo conjunto de instalaciones
        neighbor_set = current_open_set.copy()
        neighbor_set.remove(j_open)
        neighbor_set.add(j_closed)
        
        move = (j_open, j_closed) # Tupla que representa el movimiento (cerré, abrí)
        yield neighbor_set, move

def run_tabu_search(ampl_wrapper, dat_file, mod_file, n_locations, max_iterations, tabu_tenure, neighborhood_sample_size):
    """
    Ejecuta el ciclo principal de la Búsqueda Tabú.
    
    Parámetros:
    - tabu_tenure: Cuántos turnos un movimiento permanece prohibido.
    - neighborhood_sample_size: Cuántos vecinos evaluar por iteración.
    """
    
    start_time = time.time()
    print(f"\n[Heuristic] Iniciando Tabu Search | Iter: {max_iterations} | Tenure: {tabu_tenure}")

    # Estructura de memoria de corto plazo (Lista Tabú).
    # Usamos deque con maxlen para que automáticamente olvide los elementos viejos (FIFO).
    tabu_list = deque(maxlen=(tabu_tenure * 2)) 
    
    # ---------------------------------------------------------
    # 1. Generación de Solución Inicial
    # ---------------------------------------------------------
    total_demand = ampl_wrapper.get_total_demand()
    capacity_list = ampl_wrapper.get_capacity_list()
    
    current_solution_set = generate_initial_solution(n_locations, total_demand, capacity_list)
    # Evaluamos el costo llamando al Solver solo para la asignación
    current_cost = ampl_wrapper.solve_assignment_persistent(list(current_solution_set))

    # Mecanismo de reintentos: Si la solución aleatoria es infactible (costo inf), prueba otra.
    retries = 0
    while current_cost == float('inf') and retries < 10:
        retries += 1
        print(f"[Heuristic] Solución inicial infactible. Reintentando ({retries})...")
        current_solution_set = generate_initial_solution(n_locations, total_demand, capacity_list)
        current_cost = ampl_wrapper.solve_assignment_persistent(list(current_solution_set))

    # Si tras 10 intentos falla, abortamos.
    if current_cost == float('inf'):
        print("[Heuristic] ERROR: No se pudo generar una solución inicial factible.")
        return float('inf'), [], 0, []

    # Inicializamos el "Mejor Global"
    best_solution_set = current_solution_set
    best_cost = current_cost
    
    print(f"[Heuristic] Costo Inicial: {best_cost:,.2f}")

    # ---------------------------------------------------------
    # 2. Bucle Principal de Búsqueda
    # ---------------------------------------------------------
    
    # Inicializamos la lista de historial
    history = []
    # Agregamos el punto inicial
    if best_cost != float('inf'):
        history.append(best_cost)

    iterations_run = 0
    for i in range(max_iterations):
        iterations_run += 1
        
        # Variables para rastrear el mejor vecino de esta iteración
        best_neighbor_set = None
        best_neighbor_cost = float('inf')
        best_neighbor_move = None
        
        # Variables de respaldo ("Pánico"): 
        # Si todos los vecinos válidos son Tabú, guardamos el mejor Tabú para movernos hacia él si es necesario.
        best_tabu_neighbor_set = None
        best_tabu_neighbor_cost = float('inf')
        best_tabu_move = None

        # --- Exploración del Vecindario ---
        for neighbor_set, move in get_neighbors_sampled(current_solution_set, n_locations, neighborhood_sample_size):
            
            # Verificamos si el movimiento está prohibido (está en la lista tabú)
            # El movimiento es (nodo_cerrado, nodo_abierto). Chequeamos si alguno está en la lista.
            is_tabu = (move[0] in tabu_list or move[1] in tabu_list)
            
            # Llamada costosa: Resolver subproblema de transporte con Gurobi
            neighbor_cost = ampl_wrapper.solve_assignment_persistent(list(neighbor_set))
            
            if neighbor_cost == float('inf'): continue # Descartamos configuraciones infactibles

            # Criterio de Aspiración:
            # Si una solución es Tabú, pero su costo es mejor que el mejor global conocido,
            # ignoramos la prohibición y la aceptamos.
            aspiration = (neighbor_cost < best_cost)
            
            if (not is_tabu) or aspiration:
                # Es un candidato válido (no tabú o cumple aspiración)
                if neighbor_cost < best_neighbor_cost:
                    best_neighbor_cost = neighbor_cost
                    best_neighbor_set = neighbor_set
                    best_neighbor_move = move
            else:
                # Es un candidato Tabú (y no cumple aspiración). 
                # Lo guardamos solo por si no encontramos nada más.
                if neighbor_cost < best_tabu_neighbor_cost:
                    best_tabu_neighbor_cost = neighbor_cost
                    best_tabu_neighbor_set = neighbor_set
                    best_tabu_move = move

        # --- Selección del Movimiento ---
        if best_neighbor_set is not None:
            # Encontramos un vecino válido regular (o uno aspirado)
            current_solution_set = best_neighbor_set
            current_cost = best_neighbor_cost
            move_to_add = best_neighbor_move
        elif best_tabu_neighbor_set is not None:
            # Situación de "Estancamiento Parcial":
            # Todos los no-tabú eran malos o infactibles. Forzamos un movimiento Tabú para no detenernos.
            # print(f"[Heuristic] Alerta: Movimiento Tabú forzado en iter {i}")
            current_solution_set = best_tabu_neighbor_set
            current_cost = best_tabu_neighbor_cost
            move_to_add = best_tabu_move
        else:
            # Estancamiento Total: No se halló ningún vecino factible en el muestreo.
            print(f"[Heuristic] Estancamiento total en iter {i}. (Todos infactibles). Reiniciando vecindario...")
            # Aún así guardamos el historial para que no quede hueco
            history.append(best_cost)
            continue

        # Actualizar la memoria a corto plazo (Lista Tabú)
        tabu_list.append(move_to_add[0])
        tabu_list.append(move_to_add[1])

        # Actualizar el Mejor Global encontrado hasta el momento
        if current_cost < best_cost:
            best_cost = current_cost
            best_solution_set = current_solution_set
            print(f"*** [Heuristic] Nuevo Óptimo: {best_cost:,.2f} (Iter {i+1}) ***")
        else:
            # Logging reducido para no saturar la consola
            if i % 10 == 0: 
                print(f"[Heuristic] Iter {i+1}. Actual: {current_cost:,.2f} | Mejor: {best_cost:,.2f}")
        
        # Guardamos el mejor costo de esta iteración en el historial
        history.append(best_cost)

    total_time = time.time() - start_time
    print(f"\n[Heuristic] Fin. Mejor Costo: {best_cost:,.2f}. Tiempo: {total_time:.2f}s")
    
    return best_cost, list(best_solution_set), iterations_run, history