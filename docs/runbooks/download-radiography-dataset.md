# Runbook: Descargar dataset real de radiografias

> Ultima verificacion: 2026-04-21
> Responsable: Alejandro Marinas

## Cuando usar este runbook
- Cuando vayamos a **entrenar el modelo de clasificacion** de radiografias (feature 2 del backlog)
- Cuando queramos hacer una demo con imagenes medicas reales en lugar de los PNGs dummy
- **No hace falta** para correr los tests ni el pipeline del dia a dia — esos funcionan con los PNGs generados por `src/pipeline/scripts/generate_dummy_images.py`

## Prerequisitos
- Cuenta en Kaggle (gratuita)
- [Kaggle API instalada](https://github.com/Kaggle/kaggle-api): `pip install kaggle`
- Token de Kaggle en `~/.kaggle/kaggle.json` (Settings → API → Create New Token)

## Pasos

1. Configurar permisos del token (solo primera vez):
   ```bash
   chmod 600 ~/.kaggle/kaggle.json
   ```

2. Descargar el dataset (~1 GB):
   ```bash
   cd data/raw
   kaggle datasets download -d tawsifurrahman/covid19-radiography-database
   ```

3. Descomprimir:
   ```bash
   unzip covid19-radiography-database.zip -d radiography-dataset
   rm covid19-radiography-database.zip
   ```

4. Estructura esperada tras descomprimir:
   ```
   data/raw/radiography-dataset/
   ├── COVID/
   │   ├── images/          # 3616 PNGs
   │   └── masks/
   ├── Normal/
   │   ├── images/          # 10192 PNGs
   │   └── masks/
   ├── Viral Pneumonia/
   │   ├── images/          # 1345 PNGs
   │   └── masks/
   └── Lung_Opacity/
       ├── images/          # 6012 PNGs (combinar con Viral Pneumonia)
       └── masks/
   ```

## Verificacion
```bash
ls data/raw/radiography-dataset/
# Debe mostrar las 4 carpetas: COVID, Normal, "Viral Pneumonia", Lung_Opacity

find data/raw/radiography-dataset -name "*.png" | wc -l
# Debe aproximarse a 21165
```

## Si algo sale mal
- **Error 401 Unauthorized**: el token no es valido o no esta en `~/.kaggle/kaggle.json`
- **Error 403 Forbidden**: primero hay que aceptar las condiciones del dataset en la pagina de Kaggle (https://www.kaggle.com/datasets/tawsifurrahman/covid19-radiography-database)
- **Descarga lenta**: la Kaggle API descarga en serie. Es normal que tarde 5-15 minutos

## Notas sobre uso
- **No se commitea al repo** (esta en `.gitignore` como parte de `data/raw/`)
- Cada miembro del equipo descarga su copia local
- Para renombrar las imagenes al patron `HOSP-NNNNNN_*.png` que espera el `ImageIngester` habra que implementar un script adicional en la feature 2 (modelo ML)

## Historial de ejecuciones
| Fecha | Quien | Resultado | Notas |
|-------|-------|----------|-------|
