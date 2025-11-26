# Guía de Instalación y Ejecución

Sigue estos pasos en orden para configurar el entorno y ejecutar los experimentos.

## 1\. Preparación de Datos (Git LFS)

**Importante:** Este proyecto utiliza archivos de instancias grandes. Antes de configurar el código, asegúrate de tener los archivos reales y no solo los punteros.

1.  **Instalar Git LFS:** Descarga e instala desde [git-lfs.github.com](https://git-lfs.github.com/).
2.  **Activar y Descargar:**
    Desde la terminal, en la carpeta del proyecto:
    ```bash
    git lfs install
    ```
    ```bash
    git lfs pull
    ```
    *Nota: Si omites esto, obtendrás errores de tipo `invalid literal for int()` al intentar procesar los datos.*

## 2\. Configuración del Entorno Virtual

1.  **Abrir el proyecto** en VS Code (o tu terminal de preferencia).
2.  **Crear el entorno virtual:**
    ```bash
    python -m venv .venv
    ```
3.  **Activar el entorno:**
      * **Windows:**
        ```bash
        Set-ExecutionPolicy RemoteSigned -Scope Process
        ```
        ```bash
        .venv\Scripts\activate
        ```
      * **Linux/macOS:**
        ```bash
        source .venv/bin/activate
        ```
4.  **Instalar dependencias generales:**
    ```bash
    pip install -r requirements.txt
    ```

## 3\. Configuración de AMPL y Solvers

Este proyecto requiere `amplpy` y solvers externos. Con el entorno virtual activado, ejecuta:

1.  **Instalar librerías de AMPL:**
    ```bash
    python -m pip install amplpy --upgrade
    ```
    ```bash
    python -m amplpy.modules install highs gurobi
    ```
2.  **Activar tu licencia:**
    Reemplaza `(Tu Licencia)` con tu código de licencia UUID.
    ```bash
    python -m amplpy.modules activate (Tu Licencia)
    ```

## 4\. Procesamiento de Datos

Convierte las instancias de formato `.txt` a `.dat` para AMPL.

```bash
python src/main.py -a parse
```

-----

## 5\. Ejecución de Experimentos

### A) Resolver Óptimo (Exacto)

Ejecuta el solver exacto para las diferentes instancias y modos.

**Modo: Single-Source (SS)**

```bash
python src/main.py -a optimal -i Instance50x50 -m SS
```
```bash
python src/main.py -a optimal -i Instance1000x300 -m SS
```
```bash
python src/main.py -a optimal -i 2000x2000_1 -m SS
```
```bash
python src/main.py -a optimal -i 4000x4000_1 -m SS
```
```bash
python src/main.py -a optimal -i 5000x5000_1 -m SS
```

**Modo: Multi-Source (MS)**

```bash
python src/main.py -a optimal -i Instance50x50 -m MS
```
```bash
python src/main.py -a optimal -i Instance1000x300 -m MS
```
```bash
python src/main.py -a optimal -i 2000x2000_1 -m MS
```
```bash
python src/main.py -a optimal -i 4000x4000_1 -m MS
```
```bash
python src/main.py -a optimal -i 5000x5000_1 -m MS
```

### B) Resolver con Heurística

Ejecuta el algoritmo heurístico definiendo el número de iteraciones (`-n`).

**Modo: Single-Source (SS)**

> **Nota:** El problema SS con heurística sigue siendo computacionalmente costoso y podría consumir mucha RAM o tiempo en instancias grandes. Se recomienda probar la eficiencia de la heurística principalmente en modo Multi-Source.

```bash
python src/main.py -a heuristic -i Instance50x50 -m SS -n 100
```
```bash
python src/main.py -a heuristic -i Instance1000x300 -m SS -n 50
```
```bash
python src/main.py -a heuristic -i 2000x2000_1 -m SS -n 30
```
```bash
python src/main.py -a heuristic -i 4000x4000_1 -m SS -n 20
```
```bash
python src/main.py -a heuristic -i 5000x5000_1 -m SS -n 20
```

**Modo: Multi-Source (MS)**

```bash
python src/main.py -a heuristic -i Instance50x50 -m MS -n 100 -s 200
```
```bash
python src/main.py -a heuristic -i Instance1000x300 -m MS -n 200 -s 100
```
```bash
python src/main.py -a heuristic -i 2000x2000_1 -m MS -n 60 -s 30
```
```bash
python src/main.py -a heuristic -i 4000x4000_1 -m MS -n 50 -s 20
```
```bash
python src/main.py -a heuristic -i 5000x5000_1 -m MS -n 30 -s 15
```

### Graficar ejemplos para comparar Optimal vs heuristic

```bash
python src/main.py -a plot -i Instance50x50 -m MS -n 60 -s 50
```
```bash
python src/main.py -a plot -i Instance1000x300 -m MS -n 50 -s 30
```
```bash
python src/main.py -a plot -i 2000x2000_1 -m MS -n 40 -s 10
```
```bash
python src/main.py -a plot -i 4000x4000_1 -m MS -n 25 -s 5
```
```bash
python src/main.py -a plot -i 5000x5000_1 -m MS -n 20 -s 5
```