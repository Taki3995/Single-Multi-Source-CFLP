# Paso 1: Crear entorno virtual

1.- Abrir la carpeta con el proyecto en vs code
2.- crear entorno virtual ejecutando 
```bash 
python -m venv .venv 
```
3.- activar entorno:
- Windows:   
```bash
Set-ExecutionPolicy RemoteSigned -Scope Process
```
```bash
.venv\Scripts\activate
```
- Linux/macOS: 
```bash
source .venv/bin/activate
```
4.- Seleccionar interprete (usar este nuevo entorno)
5.- Instalar librerias usando el comando 
```bash
pip install -r requirements.txt
```

# Paso 2: Ejecutar Opciones:

## Transformar instancias .txt a .dat:

```bash
python src/main.py -a parse
```

Aquí tienes la sección lista para copiar y pegar en tu archivo `Instructions.md`.

-----

### Nota Importante: Error al Parsear Instancias (Git LFS)

Este proyecto utiliza **Git LFS (Large File Storage)** para manejar los archivos de instancias `.txt` que son muy grandes.

Si al ejecutar la acción `parse` (`python src/main.py -a parse`) obtienes un error similar a:

> `invalid literal for int() with base 10: 'version'`

Significa que tu sistema no ha descargado los archivos de datos reales, sino solo los "punteros" de Git LFS.

#### Solución

Para descargar los archivos de instancia correctos, sigue estos pasos en la terminal:

1.  **Instala la extensión Git LFS:**

      * Descárgala e instálala desde [git-lfs.github.com](https://git-lfs.github.com/).

2.  **Activa LFS en tu sistema:** (Solo necesitas hacerlo una vez por PC)

    ```bash
    git lfs install
    ```

3.  **Descarga los archivos:**

      * Navega hasta la carpeta del proyecto y ejecuta:

    ```bash
    git lfs pull
    ```

Después de ejecutar `git lfs pull`, los archivos `.txt` en la carpeta `data/instances_txt/` serán los correctos y el comando `parse` funcionará.

-----

## Resolver el optimo segun instancia

### Single-Source (SS)
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

### Multi-Source (MS)
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

## Resolver con heurística

### Single-Source (SS)
**NOTA: Con single source mi ram no aguanta, además, el problema usando heuristica y ss es igualmente un problema NP-hard (creo) por lo que demorará demasiado. Para probar efectivamente como funciona la heuristica y el tiempo ahorrado, probar con multi source.

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
### Multi-Source (MS)

```bash
python src/main.py -a heuristic -i Instance50x50 -m MS -n 100
```
```bash
python src/main.py -a heuristic -i Instance1000x300 -m MS -n 300
```
```bash
python src/main.py -a heuristic -i 2000x2000_1 -m MS -n 1000
```
```bash
python src/main.py -a heuristic -i 4000x4000_1 -m MS -n 1500
```
```bash
python src/main.py -a heuristic -i 5000x5000_1 -m MS -n 2000
```