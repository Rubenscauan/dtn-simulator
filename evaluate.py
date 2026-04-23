"""
evaluate.py — Análise e comparação de logs de simulação DTN.

Uso:
    # Comparar dois arquivos diretamente:
    python evaluate.py epidemic.txt mlrouter.txt

    # Comparar duas pastas com múltiplas seeds:
    python evaluate.py --dirs sim_outputs_epidemic sim_outputs_mlrouter

    # Analisar um único arquivo:
    python evaluate.py epidemic.txt
"""

import sys
import os
import glob
import statistics


# ─────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────

def detect_encoding(path):
    """Tenta UTF-16 primeiro (logs gerados pelo monitor Cell), depois latin1."""
    try:
        with open(path, "r", encoding="utf-16") as f:
            f.read(256)
        return "utf-16"
    except (UnicodeDecodeError, UnicodeError):
        return "latin1"


def parse_log(path):
    """
    Lê um arquivo de log de simulação DTN e extrai métricas.

    Formato esperado das linhas:
        <tempo>  forward  <origem>  <destino>  <msg_id>  [tag]
        <tempo>  status   <seq>     <total>    <dups>    0  <delivered>  <reached>

    Tags possíveis: 'dup', 'delivered', 'delivered,dup'
    """
    enc = detect_encoding(path)

    forwards = 0
    dups = 0
    delivered_events = 0   # contagem de eventos "delivered" (pode repetir por msg)
    delivered_msgs = set() # msgs únicas entregues
    first_delivery_time = None
    last_time = 0

    with open(path, "r", encoding=enc, errors="ignore") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue

            try:
                t = int(parts[0])
                last_time = max(last_time, t)
            except ValueError:
                continue

            event = parts[1]

            if event == "forward":
                forwards += 1
                tag = parts[5].strip() if len(parts) > 5 else ""
                msg_id = parts[4] if len(parts) > 4 else ""

                if "dup" in tag:
                    dups += 1

                if "delivered" in tag:
                    delivered_events += 1
                    delivered_msgs.add(msg_id)
                    if first_delivery_time is None:
                        first_delivery_time = t

    unique_delivered = len(delivered_msgs)
    useful = forwards - dups

    return {
        "forwards_total":    forwards,
        "forwards_useful":   useful,
        "duplicatas":        dups,
        "dup_ratio":         dups / forwards if forwards > 0 else 0.0,
        "delivered_events":  delivered_events,
        "msgs_entregues":    unique_delivered,
        "primeira_entrega":  first_delivery_time,
        "tempo_total":       last_time,
        # overhead = forwards extras por entrega única
        "overhead_ratio":    (forwards - unique_delivered) / unique_delivered
                             if unique_delivered > 0 else float("inf"),
        # eficiência = entregas únicas / total de forwards
        "eficiencia":        unique_delivered / forwards if forwards > 0 else 0.0,
    }


# ─────────────────────────────────────────────
# RELATÓRIO DE UM ÚNICO ARQUIVO
# ─────────────────────────────────────────────

def report_single(path):
    m = parse_log(path)
    name = os.path.basename(path)
    print(f"\n{'─'*50}")
    print(f"  {name}")
    print(f"{'─'*50}")
    print(f"  Forwards totais       : {m['forwards_total']}")
    print(f"  Forwards úteis        : {m['forwards_useful']}")
    print(f"  Duplicatas            : {m['duplicatas']}  ({m['dup_ratio']:.1%})")
    print(f"  Msgs únicas entregues : {m['msgs_entregues']}")
    print(f"  Eventos de entrega    : {m['delivered_events']}")
    print(f"  Primeira entrega (t)  : {m['primeira_entrega']}")
    print(f"  Tempo total sim (t)   : {m['tempo_total']}")
    print(f"  Overhead ratio        : {m['overhead_ratio']:.2f}x")
    print(f"  Eficiência            : {m['eficiencia']:.3f}")
    return m


# ─────────────────────────────────────────────
# COMPARAÇÃO DIRETA ENTRE DOIS ARQUIVOS
# ─────────────────────────────────────────────

def compare_two_files(path_a, path_b):
    ma = report_single(path_a)
    mb = report_single(path_b)

    name_a = os.path.basename(path_a)
    name_b = os.path.basename(path_b)

    print(f"\n{'═'*50}")
    print(f"  COMPARAÇÃO DIRETA")
    print(f"{'═'*50}")
    print(f"  {'Métrica':<28} {'':>2} {name_a:>12}  {name_b:>12}")
    print(f"  {'─'*28}   {'─'*12}  {'─'*12}")

    metrics = [
        ("Forwards totais",       "forwards_total",    "d"),
        ("Forwards úteis",        "forwards_useful",   "d"),
        ("Duplicatas",            "duplicatas",        "d"),
        ("Dup ratio",             "dup_ratio",         ".1%"),
        ("Msgs entregues",        "msgs_entregues",    "d"),
        ("Primeira entrega (t)",  "primeira_entrega",  "s"),
        ("Overhead ratio",        "overhead_ratio",    ".2f"),
        ("Eficiência",            "eficiencia",        ".3f"),
    ]

    for label, key, fmt in metrics:
        va = ma[key]
        vb = mb[key]
        if fmt == "s":
            sa = str(va) if va is not None else "N/A"
            sb = str(vb) if vb is not None else "N/A"
        elif fmt == "d":
            sa = f"{va:d}"
            sb = f"{vb:d}"
        elif fmt == ".1%":
            sa = f"{va:.1%}"
            sb = f"{vb:.1%}"
        else:
            sa = f"{va:{fmt}}" if va != float("inf") else "∞"
            sb = f"{vb:{fmt}}" if vb != float("inf") else "∞"
        print(f"  {label:<28}   {sa:>12}  {sb:>12}")


# ─────────────────────────────────────────────
# COMPARAÇÃO ESTATÍSTICA ENTRE DUAS PASTAS
# ─────────────────────────────────────────────

def stats_summary(values, label):
    """Retorna dict com média, mediana, desvio padrão e intervalo."""
    clean = [v for v in values if v is not None and v != float("inf")]
    if not clean:
        return {"label": label, "n": 0, "mean": None, "median": None,
                "stdev": None, "min": None, "max": None}
    return {
        "label":  label,
        "n":      len(clean),
        "mean":   statistics.mean(clean),
        "median": statistics.median(clean),
        "stdev":  statistics.stdev(clean) if len(clean) > 1 else 0.0,
        "min":    min(clean),
        "max":    max(clean),
    }


def compare_dirs(dir_a, dir_b):
    """Compara duas pastas de logs, pareando por nome de arquivo (seed)."""
    files_a = {os.path.basename(p): p
               for p in glob.glob(os.path.join(dir_a, "*.txt"))}
    files_b = {os.path.basename(p): p
               for p in glob.glob(os.path.join(dir_b, "*.txt"))}

    common = sorted(set(files_a) & set(files_b))
    if not common:
        print(f"[ERRO] Nenhum arquivo em comum entre '{dir_a}' e '{dir_b}'.")
        return

    print(f"\nSeeds em comum: {len(common)}")

    keys = ["forwards_total", "forwards_useful", "duplicatas", "dup_ratio",
            "msgs_entregues", "primeira_entrega", "overhead_ratio", "eficiencia"]

    data_a = {k: [] for k in keys}
    data_b = {k: [] for k in keys}

    for fname in common:
        ma = parse_log(files_a[fname])
        mb = parse_log(files_b[fname])
        for k in keys:
            data_a[k].append(ma[k])
            data_b[k].append(mb[k])

    name_a = os.path.basename(dir_a.rstrip("/\\"))
    name_b = os.path.basename(dir_b.rstrip("/\\"))

    labels = {
        "forwards_total":   "Forwards totais",
        "forwards_useful":  "Forwards úteis",
        "duplicatas":       "Duplicatas",
        "dup_ratio":        "Dup ratio",
        "msgs_entregues":   "Msgs entregues",
        "primeira_entrega": "1ª entrega (t)",
        "overhead_ratio":   "Overhead ratio",
        "eficiencia":       "Eficiência",
    }

    print(f"\n{'═'*70}")
    print(f"  COMPARAÇÃO ESTATÍSTICA  ({len(common)} seeds)")
    print(f"{'═'*70}")

    for k in keys:
        sa = stats_summary(data_a[k], k)
        sb = stats_summary(data_b[k], k)
        lbl = labels[k]

        print(f"\n  {lbl}")
        print(f"  {'':4} {'':12}  {'média':>10}  {'mediana':>10}  {'desvpad':>10}  {'min':>8}  {'max':>8}")
        for name, s in [(name_a, sa), (name_b, sb)]:
            if s["mean"] is None:
                print(f"  {'':4} {name:<12}  {'N/A':>10}")
                continue
            print(f"  {'':4} {name:<12}  {s['mean']:>10.2f}  {s['median']:>10.2f}"
                  f"  {s['stdev']:>10.2f}  {s['min']:>8.2f}  {s['max']:>8.2f}")

        # diferença relativa na média
        if sa["mean"] and sb["mean"] and sa["mean"] != 0:
            delta = (sb["mean"] - sa["mean"]) / sa["mean"] * 100
            arrow = "▲" if delta > 0 else "▼"
            print(f"  {'':4} Δ {name_b} vs {name_a}: {arrow} {abs(delta):.1f}%")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args:
        # modo padrão: compara epidemic.txt vs mlrouter.txt se existirem
        defaults = ["epidemic.txt", "mlrouter.txt"]
        if all(os.path.exists(p) for p in defaults):
            compare_two_files(*defaults)
        else:
            print(__doc__)
        return

    if "--dirs" in args:
        idx = args.index("--dirs")
        dirs = args[idx + 1:]
        if len(dirs) < 2:
            print("Uso: python evaluate.py --dirs <dir_a> <dir_b>")
            return
        compare_dirs(dirs[0], dirs[1])
        return

    if len(args) == 1:
        if os.path.isdir(args[0]):
            # pasta única: mostra estatísticas agregadas
            files = glob.glob(os.path.join(args[0], "*.txt"))
            if not files:
                print(f"Nenhum .txt encontrado em '{args[0]}'")
                return
            keys = ["forwards_total", "forwards_useful", "duplicatas",
                    "dup_ratio", "msgs_entregues", "primeira_entrega",
                    "overhead_ratio", "eficiencia"]
            data = {k: [] for k in keys}
            for p in files:
                m = parse_log(p)
                for k in keys:
                    data[k].append(m[k])
            name = os.path.basename(args[0].rstrip("/\\"))
            print(f"\n{'═'*50}")
            print(f"  {name}  ({len(files)} arquivos)")
            print(f"{'═'*50}")
            labels = {
                "forwards_total":   "Forwards totais",
                "forwards_useful":  "Forwards úteis",
                "duplicatas":       "Duplicatas",
                "dup_ratio":        "Dup ratio",
                "msgs_entregues":   "Msgs entregues",
                "primeira_entrega": "1ª entrega (t)",
                "overhead_ratio":   "Overhead ratio",
                "eficiencia":       "Eficiência",
            }
            for k in keys:
                s = stats_summary(data[k], k)
                if s["mean"] is None:
                    print(f"  {labels[k]:<28}: N/A")
                else:
                    print(f"  {labels[k]:<28}: média={s['mean']:.2f}  "
                          f"mediana={s['median']:.2f}  desvpad={s['stdev']:.2f}")
        else:
            report_single(args[0])
        return

    if len(args) == 2:
        if os.path.isfile(args[0]) and os.path.isfile(args[1]):
            compare_two_files(args[0], args[1])
        elif os.path.isdir(args[0]) and os.path.isdir(args[1]):
            compare_dirs(args[0], args[1])
        else:
            print("Passe dois arquivos ou duas pastas.")
        return

    print(__doc__)


if __name__ == "__main__":
    main()
