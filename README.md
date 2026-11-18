# Inscripciones de lectura cercana en el Parque de Mayo: scripts de PLN

Código de la tesina de Licenciatura en Letras (Universidad Nacional del Sur) *Lo escrito en los márgenes: inscripciones manuscritas de lectura cercana en el Parque de Mayo (Bahía Blanca)*, de Ludmila Ares, dirigida por Yolanda Hipperdinger y Lucía Cantamutto.

El corpus reúne inscripciones manuscritas relevadas en catorce zonas del Parque de Mayo y cargadas en una planilla, una fila por producción. Los scripts ordenan esa planilla, detectan problemas de carga sin corregirlos y ponen a prueba herramientas de procesamiento del lenguaje natural (tokenizadores, etiquetadores morfosintácticos y detectores de lengua) sobre un corpus situado y no estándar: fechas, usuarios de redes, sumatorias de nombres, variación ortográfica y alternancia de lenguas. La clasificación funcional de las producciones es manual; el programa solo mide cuánto se acerca a ella un clasificador automático simple.

## Contenido

| Archivo | Qué es |
|---|---|
| `ordenar_corpus.py` | Programa principal: anomalías, rasgos, tokenización comparada, frecuencias, etiquetado con spaCy y exportaciones para Voyant, Recogito y el mapa |
| `probar_freeling.py` | Etiquetado con FreeLing y comparación con spaCy |
| `probar_deteccion_lengua.py` | Detección de lengua con Lingua y langid, evaluada contra la anotación manual |
| `reproducir_muestra.py` | Reproduce el sorteo de las 200 producciones evaluadas a mano (semilla 2026) |
| `tesina_pln_corpus.ipynb` | Cuaderno de Google Colab que instala todo y corre los tres scripts, comentado línea por línea |
| `datos/corpus_ejemplo.xlsx` | Muestra anonimizada de 30 producciones, para probar los scripts (ver `datos/LEEME.md`) |
| `requirements.txt` | Bibliotecas de Python necesarias |
| `CHANGELOG.md` | Registro de cambios de cada versión |

## Cómo usarlo

**En Google Colab.** [Abrí el cuaderno en Colab](https://colab.research.google.com/github/lumilud/inscripciones-parque-de-mayo/blob/main/tesina_pln_corpus.ipynb) y corré las celdas en orden. En la sección 4 elegí la opción B, que trabaja con los datos de ejemplo.

**En una computadora propia**, con Python 3.10 o posterior:

```
pip install -r requirements.txt
python ordenar_corpus.py datos/corpus_ejemplo.xlsx --salida resultados
python probar_deteccion_lengua.py datos/corpus_ejemplo.xlsx --salida resultados
```

`probar_freeling.py` necesita además FreeLing 4.2, que se instala aparte; la sección 1 del cuaderno muestra cómo hacerlo en Ubuntu 22.04. Con `--cfg es-ar.cfg` usa la configuración del español de la Argentina, que es la de la evaluación; sin esa opción, la general (`es.cfg`).

Los scripts leen la hoja `CORPUS` de la planilla. Las columnas que usan son `ZONA`, `ID_FOTO`, `TRANSCRIPCION` y `NORMALIZACIÓN`; las de soporte, instrumento, trazo, legibilidad y lengua se usan para los conteos, y las de codificación (`FUNCION_1` y siguientes) para los cruces, cuando tienen datos.

## Resultados

Cada script deja sus archivos en la carpeta indicada con `--salida`:

| Archivo | Contenido |
|---|---|
| `01_anomalias_para_revisar.csv` | Problemas de carga: zonas fuera de rango, IDs vacíos, duplicados o ausentes, transcripciones vacías |
| `02_corpus_ordenado_con_rasgos.csv` | La planilla con categorías unificadas y una columna por rasgo detectado |
| `03_comparacion_tokenizadores.csv` | Cada producción segmentada por cuatro tokenizadores |
| `04` a `06` | Frecuencias del corpus, frecuencias por zona y bigramas |
| `07_etiquetado_spacy_para_evaluar.csv` | Una fila por token, con columnas vacías para la evaluación manual |
| `08_tabla_para_mapa.csv` | Producciones y tokens por zona |
| `resumen_corpus.xlsx` | Resumen general, una hoja por tema |
| `09` y `10` | Etiquetado con FreeLing y comparación con spaCy |
| `11` y `12` | Detección de lengua y su evaluación |

## Versiones

Cada versión publicada tiene un número (v0.1.0, v1.0.0...) y una entrada en `CHANGELOG.md` que explica qué cambió y por qué. Para repetir un análisis citado, usá la versión que figura en el texto: en el cuaderno, poné ese número en la variable `VERSION` de la sección 3.

Los resultados de la tesina se obtuvieron con Python 3.13, spaCy 3.8.18 con el modelo `es_core_news_sm` 3.8.0, NLTK 3.9.1 y FreeLing 4.2.1.

## Cómo citar

Los datos para citar el repositorio están en `CITATION.cff`; GitHub los muestra en el botón «Cite this repository».

## Licencias

- Código: licencia MIT (ver `LICENSE`).
- Documentación y datos de ejemplo: [Creative Commons Atribución 4.0 Internacional (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/deed.es).

## Desarrollo

El código se desarrolló con asistencia de un modelo de lenguaje y fue revisado y ejecutado por la autora. Las decisiones sobre qué buscar, qué se considera un dato y cómo evaluar los resultados son de la investigación, y cada resultado se revisa a mano.
