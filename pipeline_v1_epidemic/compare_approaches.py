"""
compare_approaches.py — Roda simulações para múltiplas abordagens e compara.

Uso:
    python compare_approaches.py              # roda tudo do zero
    python compare_approaches.py --skip-sim   # pula simulações, só analisa logs existentes
    python compare_approaches.py --seeds 30   # usa apenas 30 seeds

Abordagens comparadas:
    - Epidemic   (baseline flood)
    - MLRouter   (Epidemic filtrado por ML)

Os logs ficam em:
    compare_outputs/epidemic/r<seed>.txt
    compare_outputs/mlrouter/r<seed>.txt

Ao final imprime tabela comparativa com média ± desvio padrão.
"""

import os
import sys
import glob
import subprocess
import statistics

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────

PYTHON_EXE   = r".venv\Scripts\python.exe"
MAIN_SCRIPT  = "main.py"

N_SEEDS      = 30          # número de seeds (pode sobrescrever com --seeds N)
N_AGENTS     = 8
MOBILITY     = "RandomWaypoint"
MONITOR      = "Log"

OUTPUT_BASE  = "compare_outputs"

APPROACHES = {
    "epidemic": {"agent": "Epidemic"},
    "prophet":  {"agent": "ProPHET"},
    "mlrouter": {"agent": "MLRouter"},
}


# ─────────────────────────────────────────────
# PARSING (mesma lógica do evaluate.py)
# ─────────────────────────────────────────────

def detect_encoding(path):
    try:
        with open(path, "r", encoding="utf-16") as f:
            f.read(256)
        return "utf-16"
    except (UnicodeDecodeError, UnicodeError):
        return "latin1"


def parse_log(path):
    enc = detect_encoding(path)
    forwards = 0
    dups = 0
    delivered_msgs = set()
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

            if parts[1] != "forward":
                continue

            forwards += 1
            tag    = parts[5].strip() if len(parts) > 5 else ""
            msg_id = parts[4]         if len(parts) > 4 else ""

            if "dup" in tag:
                dups += 1
            if "delivered" in tag:
                delivered_msgs.add(msg_id)
                if first_delivery_time is None:
                    first_delivery_time = t

    unique_delivered = len(delivered_msgs)
    useful = forwards - dups

    return {
        "forwards_total":   forwards,
        "forwards_useful":  useful,
        "duplicatas":       dups,
        "dup_ratio":        dups / forwards if forwards > 0 else 0.0,
        "msgs_entregues":   unique_delivered,
        "primeira_entrega": first_delivery_time,
        "tempo_total":      last_time,
        "overhead_ratio":   (forwards - unique_delivered) / unique_delivered
                            if unique_delivered > 0 else None,
        "eficiencia":       unique_delivered / forwards if forwards > 0 else 0.0,
        "delivery_ratio":   1 if unique_delivered > 0 else 0,  # 1 msg no cenário
    }


# ─────────────────────────────────────────────
# SIMULAÇÕES
# ─────────────────────────────────────────────

def run_simulations(n_seeds):
    for name, cfg in APPROACHES.items():
        out_dir = os.path.join(OUTPUT_BASE, name)
        os.makedirs(out_dir, exist_ok=True)

        print(f"\n[SIM] Rodando {n_seeds} seeds para '{name}' (agent={cfg['agent']})...")

        for seed in range(1, n_seeds + 1):
            out_file = os.path.join(out_dir, f"r{seed}.txt")

            if os.path.exists(out_file):
                print(f"  seed {seed:3d} — já existe, pulando.")
                continue

            cmd = [
                PYTHON_EXE, MAIN_SCRIPT,
                "-s", str(seed),
                "-n", str(N_AGENTS),
                "-a", cfg["agent"],
                "-m", MOBILITY,
                "-M", MONITOR,
            ]

            print(f"  seed {seed:3d}...", end=" ", flush=True)
            try:
                with open(out_file, "w", encoding="latin1", errors="ignore") as f:
                    subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                        check=True,
                        timeout=120,
                    )
                print("ok")
            except subprocess.TimeoutExpired:
                print("TIMEOUT — pulando")
                if os.path.exists(out_file):
                    os.remove(out_file)
            except subprocess.CalledProcessError as e:
                print(f"ERRO (código {e.returncode})")


# ─────────────────────────────────────────────
# ANÁLISE
# ─────────────────────────────────────────────

def collect_metrics(name, n_seeds):
    out_dir = os.path.join(OUTPUT_BASE, name)
    files   = sorted(glob.glob(os.path.join(out_dir, "r*.txt")))[:n_seeds]

    if not files:
        print(f"[AVISO] Nenhum log encontrado em '{out_dir}'")
        return {}

    all_metrics = [parse_log(p) for p in files]

    keys = ["forwards_total", "forwards_useful", "duplicatas", "dup_ratio",
            "msgs_entregues", "primeira_entrega", "overhead_ratio",
            "eficiencia", "delivery_ratio"]

    aggregated = {}
    for k in keys:
        vals = [m[k] for m in all_metrics if m[k] is not None]
        if not vals:
            aggregated[k] = {"mean": None, "median": None, "stdev": None,
                             "min": None, "max": None, "n": 0}
            continue
        aggregated[k] = {
            "mean":   statistics.mean(vals),
            "median": statistics.median(vals),
            "stdev":  statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "min":    min(vals),
            "max":    max(vals),
            "n":      len(vals),
        }

    return aggregated


# ─────────────────────────────────────────────
# RELATÓRIO
# ─────────────────────────────────────────────

METRIC_LABELS = {
    "forwards_total":   ("Forwards totais",    "d",    False),  # (label, fmt, lower_is_better)
    "forwards_useful":  ("Forwards úteis",     "d",    False),
    "duplicatas":       ("Duplicatas",         "d",    True),
    "dup_ratio":        ("Dup ratio",          ".1%",  True),
    "msgs_entregues":   ("Msgs entregues",     "d",    False),
    "primeira_entrega": ("1ª entrega (t)",     ".0f",  True),
    "overhead_ratio":   ("Overhead ratio",     ".2f",  True),
    "eficiencia":       ("Eficiência",         ".3f",  False),
    "delivery_ratio":   ("Delivery ratio",     ".2f",  False),
}


def print_report(results, n_seeds):
    names = list(results.keys())

    col_w = 14
    lbl_w = 22

    header = f"  {'Métrica':<{lbl_w}}"
    for n in names:
        header += f"  {n:>{col_w}}"
    sep = "─" * len(header)

    print(f"\n{'═' * len(header)}")
    print(f"  RESULTADOS  (média ± desvpad, {n_seeds} seeds)")
    print(f"{'═' * len(header)}")
    print(header)
    print(f"  {sep}")

    for key, (label, fmt, lower_better) in METRIC_LABELS.items():
        row = f"  {label:<{lbl_w}}"
        means = []
        for name in names:
            s = results[name].get(key, {})
            if not s or s.get("mean") is None:
                row += f"  {'N/A':>{col_w}}"
                means.append(None)
                continue
            m = s["mean"]
            sd = s["stdev"]
            if fmt == "d":
                cell = f"{m:.0f} ±{sd:.0f}"
            elif fmt == ".1%":
                cell = f"{m:.1%} ±{sd:.1%}"
            else:
                cell = f"{m:{fmt}} ±{sd:{fmt}}"
            row += f"  {cell:>{col_w}}"
            means.append(m)
        print(row)

        # linha de delta entre as duas abordagens
        if len(names) == 2 and all(v is not None for v in means) and means[0] != 0:
            delta = (means[1] - means[0]) / means[0] * 100
            arrow = "▲" if delta > 0 else "▼"
            better = (lower_better and delta < 0) or (not lower_better and delta > 0)
            sign   = "✓" if better else "✗"
            print(f"  {'':>{lbl_w}}  Δ {names[1]} vs {names[0]}: "
                  f"{arrow} {abs(delta):.1f}%  {sign}")

    print(f"\n  ✓ = melhor para {names[1]}   ✗ = pior para {names[1]}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    skip_sim = "--skip-sim" in args
    n_seeds  = N_SEEDS

    for i, a in enumerate(args):
        if a == "--seeds" and i + 1 < len(args):
            try:
                n_seeds = int(args[i + 1])
            except ValueError:
                pass

    print(f"{'═'*55}")
    print(f"  DTN Comparison: {' vs '.join(APPROACHES.keys())}")
    print(f"  Seeds: {n_seeds}  |  Agentes: {N_AGENTS}  |  Mobilidade: {MOBILITY}")
    print(f"{'═'*55}")

    if not skip_sim:
        run_simulations(n_seeds)
    else:
        print("\n[INFO] --skip-sim: usando logs existentes.")

    print("\n[ANÁLISE] Coletando métricas...")
    results = {}
    for name in APPROACHES:
        results[name] = collect_metrics(name, n_seeds)

    print_report(results, n_seeds)


if __name__ == "__main__":
    main()
