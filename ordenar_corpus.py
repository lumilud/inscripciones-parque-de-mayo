"""
ordenar_corpus.py
=================
Programa de ordenamiento y exploración del corpus de inscripciones de lectura
cercana del Parque de Mayo (Bahía Blanca).

Responde a la metodología del Proyecto de Tesina en tres capas:
  1. Curaduría humana: el programa NO corrige datos; detecta anomalías y las
     informa para que la investigadora decida.
  2. Exploración asistida: frecuencias, n-gramas, rasgos gráfico-textuales y
     exportaciones para Voyant Tools, Recogito y la herramienta de mapeo.
  3. PLN propiamente dicho, puesto a prueba: tokenización comparada (NLTK vs
     spaCy) y etiquetado morfosintáctico/lematización con spaCy, sobre la
     transcripción fiel y sobre la normalización, con una columna vacía para
     que la investigadora evalúe cada etiqueta a mano.

La clasificación funcional NO se automatiza. Si la columna
CLASIFICACION_FUNCIONAL tiene datos (cargados a mano), el programa:
  (a) cruza esas categorías con los rasgos materiales (hipótesis 2), y
  (b) mide cuánto se acerca un clasificador automático simple a la
      clasificación humana (finalidad b de la metodología), como prueba de
      límites y no como sustituto.

Uso:
    pip install pandas spacy nltk scikit-learn openpyxl
    python -m spacy download es_core_news_sm
    python ordenar_corpus.py corpus.csv            # CSV exportado de la hoja CORPUS
    python ordenar_corpus.py corpus.csv --anonimizar   # para material público

Salida: carpeta resultados/ con planillas CSV, un Excel resumen y textos para
Voyant/Recogito.
"""

import argparse
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 0. Configuración
# ---------------------------------------------------------------------------

COL_ZONA = "ZONA"
COL_ID = "ID_FOTO"
COL_TRANS = "TRANSCRIPCION"
COL_NORM = "NORMALIZACIÓN"
# Clasificación manual (libro de códigos de la hoja CODIGOS, 23/10/2026).
# FUNCION_1 es la función primaria; si la planilla es anterior y no la tiene,
# se usa CLASIFICACION_FUNCIONAL.
COL_FUNC = "FUNCION_1"
COLS_CODIGOS = ["ESTRUCTURA", "COMPOSICION", "FUNCION_1", "FUNCION_2", "REGISTRO"]

# Unificación de variantes de carga (solo para contar; la planilla original no
# se modifica). Cada entrada: valor tal como aparece -> valor unificado.
UNIFICAR = {
    "INSTRUMENTO_INFERIDO": {
        "corrector/ liquid paper": "corrector/liquid paper",
        "´pintura": "pintura",
        "¿aerosol?": "aerosol (dudoso)",
        "punzon?": "punzón (dudoso)",
    },
    "ANCHO_TRAZO": {"media": "medio", "fno": "fino"},
    "LEGIBILIDAD": {"medio": "media"},
    "LENGUA": {"ingles": "inglés", "ingles?": "inglés (dudoso)",
               "español e ingles": "español e inglés"},
    "SOPORTE": {"meral": "metal"},
}

# Marcas que la transcripción usa para elementos no verbales: se conservan como
# un único token para que no se pierdan al tokenizar.
MARCA_NO_VERBAL = re.compile(r"\[(coraz[oó]n|dibujo[^\]]*|[^\]]+)\]", re.I)

# Tokenizador propio, pensado para el corpus: conserva arrobas, fechas, el signo
# "+" de las sumatorias de nombres y las marcas no verbales.
PATRON_TOKEN = re.compile(
    r"""
    \[[^\]]+\]                      # marca no verbal: [corazón]
  | @[\w.\-]+                       # usuario de red social
  | \#\w+                           # hashtag
  | \d{1,2}[/\-.]\d{1,2}(?:[/\-.]\d{2,4})?   # fecha 14/02/25, 19-6-24
  | \d+                             # número
  | \w+(?:['’]\w+)?                 # palabra
  | [+♥❤]                           # signo de unión o corazón tipográfico
    """,
    re.X,
)

# Rasgos detectables por patrón. Son DESCRIPTIVOS: orientan la lectura cercana,
# no son categorías funcionales. Cada rasgo debe validarse a mano.
RASGOS = {
    "fecha": re.compile(r"\b\d{1,2}\s*[/\-.]\s*\d{1,2}(?:\s*[/\-.]\s*\d{2,4})?\b"),
    "arroba_usuario": re.compile(r"@[\w.\-]+"),
    "sumatoria_+": re.compile(r"\w\s*\+\s*\w"),
    "sumatoria_y": re.compile(r"^\s*\w{1,12}\s+(y|e)\s+\w{1,12}\s*$", re.I),
    "marca_corazon": re.compile(r"coraz[oó]n|[♥❤]", re.I),
    "te_amo_variantes": re.compile(r"\bt[e3]\s*(re\s*)?am+o+\b|\bte\s*kiero|\bte\s*quiero", re.I),
    "insulto_o_tabú": re.compile(r"\b(puta|puto|put[oa]s|mierda|gil(es)?|petera|forro)\b", re.I),
    "grafía_k_por_qu_c": re.compile(r"\bk[eh]?e?\b|\bkiero|\bka|\bko", re.I),
    "letra_repetida": re.compile(r"([a-záéíóú])\1{2,}", re.I),
    "todo_mayúsculas": re.compile(r"^[^a-záéíóúñ]*[A-ZÁÉÍÓÚÑ]{2,}[^a-záéíóúñ]*$"),
    "signos_repetidos": re.compile(r"[!?¡¿]{2,}|\.{3,}"),
    "posible_inglés": re.compile(
        r"\b(love|you|the|stay|awake|see|again|forever|my|is|and|i)\b", re.I),
}

SALIDA = Path("resultados")


# ---------------------------------------------------------------------------
# 1. Carga y curaduría (detección de anomalías, sin corregir)
# ---------------------------------------------------------------------------

def cargar(ruta: str) -> pd.DataFrame:
    if ruta.endswith((".xlsx", ".xls")):
        df = pd.read_excel(ruta, sheet_name="CORPUS", dtype=str)
    else:
        df = pd.read_excel(ruta, sheet_name="CORPUS", dtype=str)
    df = df.fillna("")
    df.columns = [c.strip() for c in df.columns]
    if COL_FUNC not in df and "CLASIFICACION_FUNCIONAL" in df:
        df[COL_FUNC] = df["CLASIFICACION_FUNCIONAL"]
    for c in COLS_CODIGOS:
        if c not in df:
            df[c] = ""
    return df


def separar_filas_ajenas(df: pd.DataFrame):
    """La hoja CORPUS tiene al final una tablita de porcentajes por zona.
    Se separan las filas que no son producciones (ZONA no numérica)."""
    es_num = df[COL_ZONA].str.strip().str.fullmatch(r"\d+")
    vacia = (df[COL_TRANS].str.strip() == "") & (df[COL_ZONA].str.strip() == "")
    ajenas = df[~es_num & ~vacia & (df[COL_TRANS].str.strip() == "")]
    corpus = df.drop(ajenas.index)
    return corpus, ajenas


def informe_anomalias(df: pd.DataFrame) -> pd.DataFrame:
    filas = []

    def anotar(tipo, sub, detalle=""):
        for i, r in sub.iterrows():
            filas.append({"fila_planilla": i + 2, "tipo": tipo,
                          "ID_FOTO": r.get(COL_ID, ""), "ZONA": r.get(COL_ZONA, ""),
                          "TRANSCRIPCION": r.get(COL_TRANS, ""), "detalle": detalle})

    z = df[COL_ZONA].str.strip()
    anotar("zona fuera de rango (1-14) o vacía",
           df[~z.isin([str(n) for n in range(1, 15)])])
    anotar("ID_FOTO vacío", df[df[COL_ID].str.strip() == ""])
    dup = df[df[COL_ID].str.strip() != ""]
    anotar("ID_FOTO duplicado", dup[dup.duplicated(COL_ID, keep=False)])
    anotar("sin transcripción", df[df[COL_TRANS].str.strip() == ""])

    ids = pd.to_numeric(df[COL_ID], errors="coerce").dropna().astype(int)
    if len(ids):
        faltan = sorted(set(range(1, ids.max() + 1)) - set(ids))
        for f in faltan:
            filas.append({"fila_planilla": "", "tipo": "ID_FOTO ausente en la secuencia",
                          "ID_FOTO": f, "ZONA": "", "TRANSCRIPCION": "", "detalle": ""})

    # Normalizaciones que alteran el dato en lugar de regularizar la grafía
    for i, r in df[df[COL_NORM].str.strip() != ""].iterrows():
        t, n = r[COL_TRANS], r[COL_NORM]
        ft, fn = RASGOS["fecha"].findall(t), RASGOS["fecha"].findall(n)
        if ft and fn and ft != fn:
            filas.append({"fila_planilla": i + 2, "tipo": "normalización cambia formato de fecha",
                          "ID_FOTO": r[COL_ID], "ZONA": r[COL_ZONA],
                          "TRANSCRIPCION": t, "detalle": f"normalizado como: {n}"})
    return pd.DataFrame(filas)


def unificar_categorias(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col, mapa in UNIFICAR.items():
        if col in df:
            v = df[col].str.strip().str.lower()
            df[col + "_U"] = v.replace(mapa).replace("", "(sin dato)")
    return df


# ---------------------------------------------------------------------------
# 2. Tokenización (propia, NLTK y spaCy) y comparación
# ---------------------------------------------------------------------------

def tokenizar(texto: str) -> list[str]:
    return [t.lower() for t in PATRON_TOKEN.findall(texto)]


def comparar_tokenizadores(df: pd.DataFrame, nlp) -> pd.DataFrame:
    """Registra, inscripción por inscripción, cuándo los tokenizadores
    estándar segmentan distinto que el tokenizador propio. Cada diferencia es un
    dato sobre el ajuste de la herramienta al corpus."""
    from nltk.tokenize import TweetTokenizer, ToktokTokenizer
    tweet, toktok = TweetTokenizer(), ToktokTokenizer()
    filas = []
    for _, r in df.iterrows():
        t = r[COL_TRANS].strip()
        if not t:
            continue
        propio = tokenizar(t)
        tw = [x.lower() for x in tweet.tokenize(t)]
        tk = [x.lower() for x in toktok.tokenize(t)]
        sp = [x.text.lower() for x in nlp.tokenizer(t) if not x.is_space]
        filas.append({
            COL_ID: r[COL_ID], COL_TRANS: t,
            "propio": " | ".join(propio),
            "nltk_tweet": " | ".join(tw), "nltk_toktok": " | ".join(tk),
            "spacy": " | ".join(sp),
            "coinciden_todos": len({tuple(propio), tuple(tw), tuple(tk), tuple(sp)}) == 1,
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# 3. Frecuencias y n-gramas
# ---------------------------------------------------------------------------

def frecuencias(df: pd.DataFrame, col: str, por: str | None = None, n: int = 1):
    filas = []
    grupos = df.groupby(por) if por else [("corpus", df)]
    for g, sub in grupos:
        c = Counter()
        for t in sub[col]:
            toks = [x for x in tokenizar(t) if not x.startswith("[")]
            c.update(zip(*[toks[i:] for i in range(n)]))
        for k, v in c.most_common():
            filas.append({"grupo": g, "forma": " ".join(k), "frecuencia": v})
    return pd.DataFrame(filas)


def texto_para_pln(r) -> str:
    """Normalización mínima: si la investigadora la cargó, se usa; si no, la
    transcripción. Se registra cuál se usó."""
    return r[COL_NORM].strip() or r[COL_TRANS].strip()


# ---------------------------------------------------------------------------
# 4. Rasgos detectables por patrón
# ---------------------------------------------------------------------------

def detectar_rasgos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for nombre, pat in RASGOS.items():
        df["R_" + nombre] = df[COL_TRANS].apply(lambda t: bool(pat.search(t)))
    cols = [c for c in df if c.startswith("R_")]
    df["RASGOS_DETECTADOS"] = df[cols].apply(
        lambda f: ", ".join(c[2:] for c in cols if f[c]), axis=1)
    df["N_TOKENS"] = df[COL_TRANS].apply(lambda t: len(tokenizar(t)))
    return df


# ---------------------------------------------------------------------------
# 5. Etiquetado morfosintáctico y lematización con spaCy (puesta a prueba)
# ---------------------------------------------------------------------------

def etiquetar_spacy(df: pd.DataFrame, nlp) -> pd.DataFrame:
    """Etiqueta cada inscripción dos veces: transcripción fiel y texto
    normalizado (si existe). Deja la columna EVALUACION_MANUAL vacía para que la
    investigadora marque: correcto / incorrecto / dudoso, y TIPO_DE_ERROR."""
    filas = []
    for _, r in df.iterrows():
        versiones = [("transcripción", r[COL_TRANS].strip())]
        if r[COL_NORM].strip():
            versiones.append(("normalización", r[COL_NORM].strip()))
        for version, texto in versiones:
            if not texto:
                continue
            for tok in nlp(texto):
                if tok.is_space:
                    continue
                filas.append({
                    COL_ID: r[COL_ID], COL_ZONA: r[COL_ZONA], "version": version,
                    "token": tok.text, "lema": tok.lemma_, "POS": tok.pos_,
                    "rasgos_morf": str(tok.morph), "entidad": tok.ent_type_,
                    "EVALUACION_MANUAL": "", "TIPO_DE_ERROR": "",
                })
    return pd.DataFrame(filas)


def resumen_etiquetado(et: pd.DataFrame) -> pd.DataFrame:
    """Distribución de categorías POS por versión. Una proporción alta de PROPN
    o X en textos que no son nombres propios es un indicio (a verificar) de que
    el modelo no reconoce la forma."""
    if et.empty:
        return et
    # Solo se comparan las inscripciones que tienen ambas versiones; de lo
    # contrario las proporciones no serían comparables.
    pares = et.groupby(COL_ID)["version"].nunique()
    et = et[et[COL_ID].isin(pares[pares == 2].index)]
    if et.empty:
        return et
    tab = pd.crosstab(et["POS"], et["version"], normalize="columns").round(3)
    return tab.reset_index()


# ---------------------------------------------------------------------------
# 6. Exportaciones para Voyant, Recogito y mapa
# ---------------------------------------------------------------------------

def exportar_textos(df: pd.DataFrame, carpeta: Path):
    voy = carpeta / "voyant"
    voy.mkdir(parents=True, exist_ok=True)
    for z, sub in df.groupby(COL_ZONA):
        (voy / f"zona_{int(z):02d}.txt").write_text(
            "\n".join(t for t in sub[COL_TRANS] if t.strip()), encoding="utf-8")
    # Recogito: un texto plano con el ID al inicio de cada línea, para anotar y
    # georreferenciar cada producción.
    (carpeta / "recogito_corpus.txt").write_text(
        "\n".join(f"[{r[COL_ID]}] {r[COL_TRANS]}" for _, r in df.iterrows()
                  if r[COL_TRANS].strip()), encoding="utf-8")


def tabla_mapa(df: pd.DataFrame) -> pd.DataFrame:
    """Conteo por zona para unir con los polígonos del KML (columna ZONA)."""
    t = df.groupby(COL_ZONA).agg(producciones=(COL_TRANS, "count"),
                                 tokens=("N_TOKENS", "sum")).reset_index()
    t["porcentaje"] = (100 * t["producciones"] / t["producciones"].sum()).round(2)
    t[COL_ZONA] = t[COL_ZONA].astype(int)
    return t.sort_values(COL_ZONA)


# ---------------------------------------------------------------------------
# 7. Cruce con la clasificación funcional manual (cuando exista)
# ---------------------------------------------------------------------------

def cruces_materialidad(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Hipótesis 2: correlación entre categoría funcional y rasgos materiales."""
    out = {}
    lleno = df[df[COL_FUNC].str.strip() != ""]
    if lleno.empty:
        return out
    for col in ["SOPORTE_U", "INSTRUMENTO_INFERIDO_U", "ANCHO_TRAZO_U",
                "TECNICA_EJECUCION", COL_ZONA, "ESTRUCTURA", "COMPOSICION", "REGISTRO"]:
        if col in lleno and (lleno[col].str.strip() != "").any():
            out[f"cruce_{col}"] = pd.crosstab(lleno[COL_FUNC], lleno[col], margins=True)
    return out


def probar_clasificacion_automatica(df: pd.DataFrame) -> pd.DataFrame | None:
    """Compara un clasificador simple (n-gramas de caracteres + regresión
    logística, validación cruzada) con la clasificación humana. Con un corpus de
    este tamaño el resultado vale como medida de distancia entre ambas lecturas,
    no como herramienta de clasificación."""
    lleno = df[df[COL_FUNC].str.strip() != ""]
    if lleno[COL_FUNC].nunique() < 2 or len(lleno) < 30:
        return None
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict, StratifiedKFold
    from sklearn.pipeline import make_pipeline
    y = lleno[COL_FUNC].str.strip()
    k = min(5, y.value_counts().min())
    if k < 2:
        return None
    modelo = make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), lowercase=True),
        LogisticRegression(max_iter=1000, class_weight="balanced"))
    pred = cross_val_predict(modelo, lleno[COL_TRANS], y,
                             cv=StratifiedKFold(k, shuffle=True, random_state=0))
    res = lleno[[COL_ID, COL_TRANS]].copy()
    res["humana"], res["automatica"] = y.values, pred
    res["coincide"] = res["humana"] == res["automatica"]
    return res


# ---------------------------------------------------------------------------
# 8. Anonimización (para diapositivas o material público)
# ---------------------------------------------------------------------------

def anonimizar(texto: str, nlp) -> str:
    """Primera pasada automática: requiere revisión manual. En la prueba con
    el corpus, spaCy etiquetó como nombre propio muchas formas escritas en
    mayúsculas (RESPIRAR AL [nombre]...), de modo que la anonimización excede
    lo necesario. Ese exceso es, en sí mismo, un dato sobre la herramienta."""
    texto = re.sub(r"@[\w.\-]+", "@[usuario]", texto)
    doc = nlp(texto)
    partes = []
    for tok in doc:
        if tok.ent_type_ == "PER" or (tok.pos_ == "PROPN" and tok.text[:1].isupper()):
            partes.append("[nombre]" + tok.whitespace_)
        else:
            partes.append(tok.text_with_ws)
    return "".join(partes)


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo", help="CSV o XLSX exportado de la hoja CORPUS")
    ap.add_argument("--anonimizar", action="store_true",
                    help="reemplaza nombres y usuarios en las exportaciones de texto")
    ap.add_argument("--salida", default=str(SALIDA))
    a = ap.parse_args()
    out = Path(a.salida)
    out.mkdir(exist_ok=True)

    import spacy
    nlp = spacy.load("es_core_news_sm")

    bruto = cargar(a.archivo)
    corpus, ajenas = separar_filas_ajenas(bruto)
    anom = informe_anomalias(corpus)
    anom.to_csv(out / "01_anomalias_para_revisar.csv", index=False)

    # Solo se analizan producciones con zona válida y transcripción
    valido = corpus[corpus[COL_ZONA].str.strip().isin([str(n) for n in range(1, 15)])
                    & (corpus[COL_TRANS].str.strip() != "")].copy()
    valido = unificar_categorias(valido)
    valido = detectar_rasgos(valido)
    if a.anonimizar:
        valido[COL_TRANS] = valido[COL_TRANS].apply(lambda t: anonimizar(t, nlp))

    valido.to_csv(out / "02_corpus_ordenado_con_rasgos.csv", index=False)
    tok = comparar_tokenizadores(valido, nlp)
    tok.to_csv(out / "03_comparacion_tokenizadores.csv", index=False)
    frec = frecuencias(valido, COL_TRANS)
    frec.to_csv(out / "04_frecuencias_corpus.csv", index=False)
    frecz = frecuencias(valido, COL_TRANS, por=COL_ZONA)
    frecz.to_csv(out / "05_frecuencias_por_zona.csv", index=False)
    bi = frecuencias(valido, COL_TRANS, n=2)
    bi.to_csv(out / "06_bigramas.csv", index=False)
    et = etiquetar_spacy(valido, nlp)
    et.to_csv(out / "07_etiquetado_spacy_para_evaluar.csv", index=False)
    mapa = tabla_mapa(valido)
    mapa.to_csv(out / "08_tabla_para_mapa.csv", index=False)
    exportar_textos(valido, out)

    rasgos = valido[[c for c in valido if c.startswith("R_")]].sum().rename(
        lambda c: c[2:]).sort_values(ascending=False).rename("producciones").reset_index()
    rasgos.columns = ["rasgo", "producciones"]
    materiales = {c: valido[c].value_counts().rename_axis(c).reset_index(name="n")
                  for c in ["SOPORTE_U", "INSTRUMENTO_INFERIDO_U", "ANCHO_TRAZO_U",
                            "TECNICA_EJECUCION", "LEGIBILIDAD_U", "LENGUA_U"] if c in valido}

    tokens = [x for t in valido[COL_TRANS] for x in tokenizar(t) if not x.startswith("[")]
    resumen = pd.DataFrame([
        ("filas en la hoja", len(bruto)),
        ("filas ajenas al corpus (tabla de porcentajes)", len(ajenas)),
        ("producciones analizadas (zona 1-14 y con transcripción)", len(valido)),
        ("tokens (tokenizador propio, sin marcas no verbales)", len(tokens)),
        ("formas distintas", len(set(tokens))),
        ("producciones con normalización cargada", (valido[COL_NORM].str.strip() != "").sum()),
        ("producciones con clasificación funcional cargada", (valido[COL_FUNC].str.strip() != "").sum()),
        ("inscripciones donde los 4 tokenizadores coinciden", int(tok["coinciden_todos"].sum())),
        ("anomalías registradas para revisar", len(anom)),
    ], columns=["indicador", "valor"])

    with pd.ExcelWriter(out / "resumen_corpus.xlsx") as xw:
        resumen.to_excel(xw, sheet_name="resumen", index=False)
        anom.to_excel(xw, sheet_name="anomalias", index=False)
        mapa.to_excel(xw, sheet_name="por_zona", index=False)
        rasgos.to_excel(xw, sheet_name="rasgos_detectados", index=False)
        for c, t in materiales.items():
            t.to_excel(xw, sheet_name=c[:31], index=False)
        frec.head(60).to_excel(xw, sheet_name="frecuencias_top", index=False)
        bi.head(40).to_excel(xw, sheet_name="bigramas_top", index=False)
        resumen_etiquetado(et).to_excel(xw, sheet_name="POS_por_version", index=False)
        for nombre, t in cruces_materialidad(valido).items():
            t.to_excel(xw, sheet_name=nombre[:31])
        clas = probar_clasificacion_automatica(valido)
        if clas is not None:
            clas.to_excel(xw, sheet_name="clasif_humana_vs_auto", index=False)

    print(resumen.to_string(index=False))
    if (valido[COL_FUNC].str.strip() == "").all():
        print("\nFUNCION_1 está vacía: los cruces con la materialidad y la "
              "prueba de clasificación automática se activarán cuando la cargues.")
    print(f"\nResultados en: {out.resolve()}")


if __name__ == "__main__":
    sys.exit(main())
