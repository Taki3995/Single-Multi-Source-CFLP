REESCRIBIR, AHORA TIENE TODA LA INDO, EN LA ENTREGA DEBE TENER SOLO LO ESCENCIAL

SE IMPLEMENTARA LA HEURISTICA BUSQUEDA TABU (TABU SEARCH)
# Instrucciones del Proyecto: Optimización Híbrida para el CFLP

## 1. Objetivo General
El objetivo de este proyecto es diseñar, implementar y evaluar una solución de optimización híbrida para resolver el Problema de Localización de Instalaciones con Capacidad (CFLP).

Esta solución combinará un algoritmo heurístico, que se encargará de seleccionar las localizaciones de los centros, con un algoritmo exacto (usando AMPL/JuMP + Solver), que determinará la asignación óptima de clientes a dichos centros.

## 2. Descripción del Problema (CFLP)
El modelo a implementar, definido en el archivo CFLP.mod, busca minimizar el costo total, que se compone de dos partes:

1.- Costo Fijo: La suma del costo fijo (fc) por cada localización que se decide abrir.

2.- Costo de Asignación: La suma del costo de transporte por asignar cada cliente i a una localización j.

**Parámetros del Modelo**
- Clientes y Localizaciones.

- Capacidad de cada localización.

- Costo Fijo (fc) de abrir cada localización.

- Demanda de cada cliente.

- Costo de Transporte desde un cliente i a una localización j.

**Variables de Decisión**
- Vector de Localizaciones (binario): Indica si una localización está abierta (1) o cerrada (0).

- Matriz de Asignación (binaria): Indica si un cliente i es asignado (1) o no asignado (0) a una localización j.

**Restricciones Principales**
- Restricción de Asignación: (Para el modelo single-source) Cada cliente debe ser asignado exactamente a un solo centro.

- Restricción de Capacidad: La suma total de la demanda de los clientes asignados a un centro no puede superar la capacidad de dicho centro.

## 3. Requisitos Técnicos de Implementación
La solución desarrollada debe cumplir con los siguientes requisitos:

- Portabilidad: Poder ser ejecutado, como mínimo, en sistemas operativos Linux y MS-Windows.

- Modelado: Utilizar AMPL o JuMP.

- Solver:

    - Si se usa JuMP, se debe emplear Gurobi.

    - Si se usa AMPL, se puede utilizar cualquier solver incluido en el paquete de AMPL (ej. Gurobi, CPLEX, etc.).

## 4. Tarea Central: El Algoritmo Híbrido
Se debe implementar un algoritmo que divida la solución en dos niveles: una heurística para la selección y un modelo exacto para la asignación.

1.- Algoritmo Heurístico (Nivel Superior):

- Función: Será el encargado de buscar y proponer "buenas" combinaciones de centros abiertos (es decir, generar el vector binario de localizaciones).

- Elección: El grupo puede elegir la heurística que estime conveniente (ej. Búsqueda Local, Simulated Annealing, VNS, etc.).

2.- Algoritmo Exacto (Nivel Inferior):

- Función: Será el encargado de encontrar la asignación óptima de clientes, dado un conjunto fijo de centros abiertos que ha sido determinado por la heurística.

- Implementación: Corresponde al modelo CFLP.mod (AMPL/JuMP) que resuelve el problema de asignación.

**Flujo de Ejecución (Ejemplo con Búsqueda Local)**
El algoritmo debe facilitar la "conversación" entre la heurística y el solver:

1.- La heurística genera una solución inicial (un vector de centros abiertos, ej. [1, 0, 1, 0, ...]).

2.- Este vector se pasa al modelo AMPL/JuMP.

3.- AMPL/JuMP resuelve el problema de asignación óptimo para esos centros específicos y devuelve el costo total (costo fijo de esos centros + costo de transporte de la asignación).

4.- La heurística (ej. Búsqueda Local) recibe ese costo. Luego, genera una solución "vecina" (un nuevo vector, ej. [1, 1, 1, 0, ...], abriendo un centro y cerrando otro).

5.- Este nuevo vector se pasa nuevamente a AMPL/JuMP, que calcula el costo total para esta nueva configuración.

6.- El proceso se repite, explorando el espacio de búsqueda de localizaciones.

**Criterios de Término**
El algoritmo híbrido deberá tener como criterio de término:

- Un número de iteraciones máximo (que debe poder ser ingresado por el usuario).

- O, haber alcanzado la solución óptima del problema (si esta se conoce).

## 5. Alcance y Variantes del Problema
**Instancias**
- El programa debe ser capaz de procesar y resolver instancias del CFLP de diversos tamaños, desde 50x50 hasta 5000x5000 (clientes x localizaciones).

**Procesamiento de Datos**
- Se proveen instancias en formato .txt (ej. 2000x2000_1.txt), cuyo formato se detalla en OR-Library.

- Se debe implementar una funcionalidad que lea estos archivos .txt y los transforme automáticamente al formato .dat requerido por AMPL (similar a los archivos Instance50x50.dat provistos como ejemplo).

**Variantes del Modelo (Single vs. Multi-Source)**
Se debe encontrar la solución óptima (con el algoritmo híbrido) para cada instancia, considerando dos variantes del problema:

- Single-Source (Fuente Única): El problema base descrito, donde cada cliente se atiende solamente desde un centro.

- Multi-Source (Fuente Múltiple): Se debe modificar el modelo para permitir que la demanda de un cliente pueda ser atendida por más de un centro (lo que implica un cambio en las variables de decisión y/o restricciones).

## 6. Archivos Proporcionados
- 2000x2000_1.txt, 4000x4000_1.txt, 5000x5000_1.txt: Instancias grandes en formato texto (OR-Library) que deben ser convertidas.

- CFLP.mod: Archivo de modelo AMPL que define la lógica del problema (parámetros, variables, objetivo y restricciones).

- Instance50x50.dat, instance1000x300.dat: Ejemplos de instancias en formato .dat que AMPL puede leer. Usar como referencia para la conversión.

- logfile.txt: Archivo de registro.

## 7. Formato de Entrega
La entrega consiste en un único archivo .zip que debe contener:

1.- Archivos del Programa: Todos los archivos fuente, scripts y módulos (.mod, .dat, etc.) necesarios para la correcta ejecución de la solución completa.

2.- Planilla de Resultados (Excel/CSV):

- Esta planilla debe comparar, para cada instancia (y para ambas variantes, single y multi-source):

    - El valor de la solución óptima real (obtenida resolviendo la instancia solo con AMPL/Gurobi).

    - El valor de la mejor solución encontrada por el algoritmo híbrido implementado.

- Esto permitirá comparar qué tan difícil fue para la heurística encontrar el óptimo en instancias más grandes.

3.- Archivos de la Mejor Solución:

- Por cada instancia, se debe incluir un archivo de salida (ej. .txt) con la mejor solución encontrada por el algoritmo híbrido.

- Este archivo debe detallar:

    - El vector de centros (cuáles están abiertos).

    - La matriz de asignación (qué cliente está asignado a qué centro).

- Nota: Para matrices de asignación muy grandes (ej. 5000x5000), es aceptable reducir el formato a una lista de pares (cliente, centro_asignado) en lugar de la matriz binaria completa.

# instalacion: como preparar el entorno

1. Clonar el repositorio
git clone ...
cd CFLP_PROYECTO

2. Crear y activar el entorno virtual
python -m venv .venv
source .venv/bin/activate  # (o .venv\Scripts\activate en Windows)

3. Instalar dependencias
pip install -r requirements.txt


Uso / Ejecución: El comando exacto para correr el programa.

# Ejemplo de cómo ejecutar el main.py
python src/main.py --instance "2000x2000_1" --iterations 500 --mode "SS"


# Estructura de archivos

CFLP_PROYECTO/
├── .venv/                        # Entorno virtual de Python
├── data/
│   ├── instances_txt/            # Instancias en formato txt
│   ├── instances_dat/            # instancias en formato dat
│   └── solutions/                # resultados mejores soluciones encontradas por heuristica + AMPL
│
├── models/
│   ├── cflp_MultiSource.mod      # Modelo que encuentra el óptimo MultiSource
│   └── cflp_SingleSource.mod     # Modelo que encuentra el óptimo SingleSource
│
├── src/
│   ├── __init__.py
│   ├── main.py                   # Punto de entrada principal para ejecutar todo
│   ├── data_parser.py            # Script para convertir .txt -> .dat
│   ├── heuristic.py              # Lógica de heurística Tabu Search. Propone combinaciones de centros
│   ├── ampl_solver.py            # Interfaz para llamar a AMPL desde Python. Dos funciones (solo AMPL y AMPL + Heuristic)
│   └──utils.py                   # funciones utilidades
│
├── .gitignore                    # Para ignorar .venv, __pycache__, etc.
├── requirements.txt              # Lista de librerías (amplpy, pandas)
├── Instructions.md               # Instrucciones para ejecutar trabajo
└── report.xlsx                   # Reporte completo de soluciones encontradas para cada instancia