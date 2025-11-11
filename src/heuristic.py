"""
Implementa la logica de la heurística a eleccion
En este caso, se implementará Tabu Search
"""

import os
import random
from amplpy import AMPL
import ampl_solver # Importamos nuestro "motor"
from collections import deque # Usaremos una 'deque' para la lista tabú

# --- Parámetros de la Heurística de Búsqueda Tabú ---

# Cuántos centros abrir en la solución inicial.
NUM_FACILITIES_TO_OPEN_INITIAL = 50 

# Tamaño de la "memoria": cuántas iteraciones un "movimiento"
# permanece prohibido (tabú). Un buen punto de partida es 7.
TABU_TENURE = 7 

# Cuántos vecinos generar y evaluar en CADA iteración.
# Un valor más grande da mejores decisiones, pero es más lento.
NEIGHBORHOOD_SIZE = 20


def get_initial_solution(all_locations, num_to_open):
    """
    Genera una solución inicial aleatoria.
    (Esta función no cambia)
    """
    print(f"[Heuristic] Generando solución inicial con {num_to_open} centros.")
    try:
        k = min(num_to_open, len(all_locations))
        initial_solution = random.sample(all_locations, k)
        return initial_solution
    except Exception as e:
        print(f"[Heuristic] Error al crear solución inicial: {e}")
        return []

def get_neighborhood(current_open_list, all_locations_list, n_size):
    """
    Genera un "vecindario" de N_SIZE soluciones vecinas.
    Cada vecino se crea con un intercambio (SWAP).
    
    Retorna: una lista de tuplas: [(vecino_1, movimiento_1), (vecino_2, movimiento_2), ...]
    donde 'vecino' es la lista de centros y 'movimiento' es (cerrado, abierto).
    """
    
    neighborhood = []
    
    open_set = set(current_open_list)
    all_set = set(all_locations_list)
    closed_list = list(all_set - open_set)
    open_list = list(open_set) # Usar la lista para random.choice
    
    if not closed_list or not open_list:
        return [] # No se pueden hacer intercambios

    for _ in range(n_size):
        try:
            # 1. Elegir uno para cerrar
            to_close = random.choice(open_list)
            
            # 2. Elegir uno para abrir
            to_open = random.choice(closed_list)

            # 3. Crear la nueva solución vecina
            neighbor_set = (open_set - {to_close}) | {to_open}
            
            # Guardar el vecino y el movimiento que lo generó
            move = (to_close, to_open)
            neighborhood.append( (list(neighbor_set), move) )
        except IndexError:
            # Pasa si closed_list o open_list se agotan (raro)
            break
            
    return neighborhood


def run_tabu_search(dat_file, mod_file, iterations):
    """
    Función principal que ejecuta la Búsqueda Tabú Híbrida.
    """
    print(f"[Heuristic] Iniciando Búsqueda Tabú Híbrida...")
    
    # --- 1. Obtener datos de la instancia ---
    try:
        temp_ampl = AMPL()
        temp_ampl.readData(dat_file)
        ALL_LOCATIONS = temp_ampl.getSet('LOCATIONS').getValues().toList()
        temp_ampl.close()
        if not ALL_LOCATIONS:
            raise Exception("No se pudieron leer las localizaciones del .dat")
    except Exception as e:
        print(f"[Heuristic] Error crítico al leer {dat_file}: {e}")
        return None, None, None

    # --- 2. Solución Inicial ---
    n_initial = min(NUM_FACILITIES_TO_OPEN_INITIAL, len(ALL_LOCATIONS))
    current_solution = get_initial_solution(ALL_LOCATIONS, n_initial)
    
    # Evaluar la solución inicial
    current_cost = ampl_solver.solve_assignment(dat_file, mod_file, current_solution)
    
    if current_cost == float('inf'):
        print("[Heuristic] ¡Error! La solución inicial no es factible.")
        return None, None, None
        
    # En Búsqueda Tabú, 'current' y 'best' son distintos.
    # 'current' se mueve, 'best' solo guarda al mejor de todos.
    best_solution = current_solution
    best_cost = current_cost
    
    # La "memoria": una cola que guarda los últimos K movimientos.
    # Usamos maxlen para que automáticamente olvide movimientos antiguos.
    tabu_list = deque(maxlen=TABU_TENURE)
    
    print(f"[Heuristic] Iter 0 (Inicial): Costo = {best_cost:,.2f}")

    # --- 3. Bucle de Búsqueda Tabú ---
    for i in range(1, iterations + 1):
        
        # a. Generar el vecindario
        neighborhood = get_neighborhood(current_solution, ALL_LOCATIONS, NEIGHBORHOOD_SIZE)
        if not neighborhood:
            print("[Heuristic] No se pueden generar más vecinos. Deteniendo.")
            break
            
        best_neighbor = None
        best_neighbor_cost = float('inf')
        best_neighbor_move = None

        # b. Evaluar el vecindario
        for neighbor, move in neighborhood:
            
            # Evaluar el costo del vecino
            neighbor_cost = ampl_solver.solve_assignment(dat_file, mod_file, neighbor)

            # --- Lógica Tabú y de Aspiración ---
            
            # El movimiento inverso (abrir, cerrar) también es tabú
            reverse_move = (move[1], move[0]) 
            
            is_tabu = (move in tabu_list) or (reverse_move in tabu_list)
            
            # Criterio de Aspiración:
            # Si el movimiento es tabú, PERO produce una solución
            # mejor que la MEJOR GLOBAL encontrada, ¡lo permitimos!
            aspiration_met = (neighbor_cost < best_cost)
            
            if (not is_tabu) or (aspiration_met):
                # Este vecino es un candidato válido
                if neighbor_cost < best_neighbor_cost:
                    best_neighbor = neighbor
                    best_neighbor_cost = neighbor_cost
                    best_neighbor_move = move
            
            # (Si todos los vecinos son tabú, no nos moveremos)
        
        # c. Moverse al mejor vecino no-tabú
        if best_neighbor is None:
            print(f"[Heuristic] Iter {i}: Todos los vecinos eran tabú. No hay movimiento.")
            continue
            
        # Realizar el movimiento (¡incluso si es peor que 'current_cost'!)
        current_solution = best_neighbor
        current_cost = best_neighbor_cost
        
        # Añadir el movimiento a la lista tabú
        tabu_list.append(best_neighbor_move)
        
        # d. Actualizar la mejor solución global (si aplica)
        if current_cost < best_cost:
            best_solution = current_solution
            best_cost = current_cost
            print(f"[Heuristic] Iter {i}: Nuevo Mejor Costo = {best_cost:,.2f} (Mov: {best_neighbor_move})")
        
        # Imprimir de vez en cuando para saber que sigue vivo
        elif i % 10 == 0:
            print(f"[Heuristic] Iter {i}: Costo actual = {current_cost:,.2f} (Mejor: {best_cost:,.2f})")

    
    print(f"[Heuristic] Búsqueda finalizada. Mejor costo encontrado: {best_cost:,.2f}")

    # --- 4. Obtener Asignaciones Finales ---
    print(f"[Heuristic] Obteniendo asignaciones para la mejor solución...")
    
    # Esta función ya la añadimos a ampl_solver.py en el paso anterior
    best_assignments = ampl_solver.get_assignments_for_solution(
        dat_file, mod_file, best_solution
    )

    if best_assignments is None:
        print("[Heuristic] Error: No se pudieron obtener las asignaciones finales.")

    # --- 5. Retornar todo ---
    return best_cost, best_solution, best_assignments