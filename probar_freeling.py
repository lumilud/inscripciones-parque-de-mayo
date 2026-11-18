"""
probar_freeling.py
==================
Somete el corpus al etiquetado morfosintáctico y la lematización de FreeLing
(analizador `analyze`) sobre la transcripción fiel y sobre la normalización, y deja una tabla para evaluar cada etiqueta a mano.
Es la misma prueba que ordenar_corpus.py hace con spaCy, para compararlas.

Requiere FreeLing instalado (ver instrucciones de instalación en Colab).

Uso:
    python probar_freeling.py corpus.csv                      # configuración general (es.cfg)
    python probar_freeling.py corpus.csv --cfg es-ar.cfg      # español de la Argentina
    python probar_freeling.py corpus.csv --salida resultados

La evaluación manual de la ponencia y del artículo se hizo con --cfg es-ar.cfg.

Salida en resultados/:
    09_etiquetado_freeling_para_evaluar.csv   una fila por token
    10_freeling_vs_spacy.csv                  comparación por producción
                                              (solo si existe 07_etiquetado_spacy_para_evaluar.csv)

Las etiquetas de FreeLing siguen el sistema EAGLES: la primera letra indica la
clase (N sustantivo, V verbo, A adjetivo, P pronombre, R adverbio, D
determinante, S preposición, C conjunción, Z número, W fecha, F puntuación,
I interjección). NP es nombre propio.
"""

import argparse
import subprocess
from pathlib import Path

import pandas as pd

from ordenar_corpus import cargar, separar_filas_ajenas, COL_ID, COL_ZONA, COL_TRANS, COL_NORM

SEPARADOR = "zzzseparadorzzz"
CLASES = {"N": "NOUN/PROPN", "V": "VERB/AUX", "A": "ADJ", "P": "PRON", "R": "ADV",
          "D": "DET", "S": "ADP", "C": "CONJ", "Z": "NUM", "W": "FECHA",
          "F": "PUNCT", "I": "INTJ"}


def analizar(textos: list[str], cfg: str = "es.cfg") -> list[list[tuple[str, str, str, str]]]:
    """Una sola llamada a FreeLing para todo el corpus. A cada texto se le
    agrega un punto final, para que FreeLing lo trate como una oración aparte
    (en la prueba, la opción --flush no separó las líneas y el reconocedor de
    entidades unía nombres de producciones distintas), y entre textos se
    intercala un separador. Ese punto agregado se descarta del resultado."""
    entrada = "\n".join(f"{t} .\n{SEPARADOR} ." for t in textos) + "\n"
    proc = subprocess.run(["analyze", "-f", cfg, "--outlv", "tagged"],
                          input=entrada, capture_output=True, text=True, check=True)
    resultados, actual = [], []
    for linea in proc.stdout.splitlines():
        partes = linea.split(" ")
        if len(partes) < 3:
            continue
        forma, lema, etiqueta = partes[0], partes[1], partes[2]
        prob = partes[3] if len(partes) > 3 else ""
        if forma == SEPARADOR:
            resultados.append(actual)
            actual = []
        else:
            actual.append((forma, lema, etiqueta, prob))
    limpio = []
    for i, toks in enumerate(resultados):
        if i > 0 and toks and toks[0][0] == ".":
            toks = toks[1:]          # punto que cerraba el separador anterior
        if toks and toks[-1][0] == ".":
            toks = toks[:-1]         # punto agregado al final del texto
        limpio.append(toks)
    if len(limpio) != len(textos):
        raise RuntimeError(f"FreeLing devolvió {len(limpio)} bloques para {len(textos)} textos")
    return limpio


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo")
    ap.add_argument("--salida", default="resultados")
    ap.add_argument("--cfg", default="es.cfg",
                    help="configuración de FreeLing: es.cfg (general) o es-ar.cfg (Argentina)")
    a = ap.parse_args()
    out = Path(a.salida)
    out.mkdir(exist_ok=True)

    corpus, _ = separar_filas_ajenas(cargar(a.archivo))
    valido = corpus[corpus[COL_ZONA].str.strip().isin([str(n) for n in range(1, 15)])
                    & (corpus[COL_TRANS].str.strip() != "")]

    filas = []
    for version, col in [("transcripción", COL_TRANS), ("normalización", COL_NORM)]:
        sub = valido[valido[col].str.strip() != ""]
        textos = [" ".join(t.split()) for t in sub[col]]
        for (_, r), toks in zip(sub.iterrows(), analizar(textos, a.cfg)):
            for forma, lema, etiqueta, prob in toks:
                filas.append({COL_ID: r[COL_ID], COL_ZONA: r[COL_ZONA], "version": version,
                              "token": forma, "lema": lema, "etiqueta_EAGLES": etiqueta,
                              "clase": CLASES.get(etiqueta[:1], etiqueta[:1]),
                              "nombre_propio": etiqueta.startswith("NP"), "probabilidad": prob,
                              "EVALUACION_MANUAL": "", "TIPO_DE_ERROR": ""})
    et = pd.DataFrame(filas)
    et.to_csv(out / "09_etiquetado_freeling_para_evaluar.csv", index=False)

    tr = et[et.version == "transcripción"]
    print(f"Configuración de FreeLing: {a.cfg}")
    print(f"Tokens etiquetados (transcripción): {len(tr)}")
    print(f"Proporción de nombres propios (NP): {tr.nombre_propio.mean():.1%}")
    print(tr["clase"].value_counts(normalize=True).round(3).to_string())

    sp = out / "07_etiquetado_spacy_para_evaluar.csv"
    if sp.exists():
        s = pd.read_csv(sp, dtype=str).fillna("")
        s = s[s.version == "transcripción"]
        comp = []
        for idf, g in tr.groupby(COL_ID, sort=False):
            gs = s[s[COL_ID] == str(idf)]
            comp.append({COL_ID: idf,
                         "freeling": " | ".join(f"{t}/{e}" for t, e in zip(g.token, g.etiqueta_EAGLES)),
                         "spacy": " | ".join(f"{t}/{p}" for t, p in zip(gs.token, gs.POS)),
                         "NP_freeling": int(g.nombre_propio.sum()),
                         "PROPN_spacy": int((gs.POS == "PROPN").sum())})
        pd.DataFrame(comp).to_csv(out / "10_freeling_vs_spacy.csv", index=False)
        print("Comparación con spaCy guardada en 10_freeling_vs_spacy.csv")
    print(f"Resultados en: {out.resolve()}")


if __name__ == "__main__":
    main()
