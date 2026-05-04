import os
import csv
import glob
import subprocess
import pandas as pd

# =========================
# CONFIGURACAO
# =========================
PYTHON_EXE = r".venv\Scripts\python.exe"
MAIN_SCRIPT = "main.py"

N_SIMULATIONS = 150
N_AGENTS = 8
AGENT = "Epidemic"
MOBILITY = "RandomWaypoint"
MONITOR = "Log"

OUTPUT_DIR = "sim_outputs"
CSV_DIR = "csv_outputs"
FINAL_DATASET = "dataset_final.csv"

CLEAR_OLD_FILES = True


# =========================
# GARANTIR PASTAS
# =========================
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)


def cleanup_old_files():
    if not CLEAR_OLD_FILES:
        return

    for pattern in [
        os.path.join(OUTPUT_DIR, "r*.txt"),
        os.path.join(CSV_DIR, "r*.csv"),
    ]:
        for file in glob.glob(pattern):
            os.remove(file)

    if os.path.exists(FINAL_DATASET):
        os.remove(FINAL_DATASET)

    print("[CLEANUP] Arquivos antigos removidos.")


# =========================
# 1. RODAR SIMULACOES
# =========================
def run_simulations():
    for seed in range(1, N_SIMULATIONS + 1):
        txt_file = os.path.join(OUTPUT_DIR, f"r{seed}.txt")

        cmd = [
            PYTHON_EXE,
            MAIN_SCRIPT,
            "-s", str(seed),
            "-n", str(N_AGENTS),
            "-a", AGENT,
            "-m", MOBILITY,
            "-M", MONITOR,
        ]

        print(f"[SIM] Rodando seed {seed}...")

        with open(txt_file, "w", encoding="latin1", errors="ignore") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)

        print(f"[SIM] Seed {seed} salva em {txt_file}")


# =========================
# 2. CONVERTER TXT -> CSV
# =========================
def convert_txt_to_csv():
    txt_files = glob.glob(os.path.join(OUTPUT_DIR, "r*.txt"))

    for txt_file in txt_files:
        rows = []

        # controle de quem ja recebeu cada msg_id
        msg_receivers = {}

        with open(txt_file, "r", encoding="latin1", errors="ignore") as f:
            for line in f:
                parts = line.strip().split("\t")

                if len(parts) >= 5 and parts[1] == "forward":
                    tempo = int(parts[0])
                    origem = int(parts[2])
                    destino = int(parts[3])
                    msg_id = parts[4]
                    delivered = 1 if len(parts) > 5 and parts[5] == "delivered" else 0

                    # inicializa conjunto de receptores da mensagem
                    if msg_id not in msg_receivers:
                        msg_receivers[msg_id] = set()

                        # tenta inferir origem inicial da msg a partir do formato "1-2-1"
                        try:
                            source_node = int(msg_id.split("-")[0])
                            msg_receivers[msg_id].add(source_node)
                        except Exception:
                            pass

                    # label novo: encaminhamento util
                    # 1 se destino ainda nao tinha a mensagem
                    forward_util = 1 if destino not in msg_receivers[msg_id] else 0

                    # atualiza estado: agora destino passa a ter a mensagem
                    msg_receivers[msg_id].add(destino)

                    rows.append([
                        tempo,
                        origem,
                        destino,
                        msg_id,
                        delivered,
                        forward_util
                    ])

        csv_name = os.path.basename(txt_file).replace(".txt", ".csv")
        csv_file = os.path.join(CSV_DIR, csv_name)

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "tempo",
                "origem",
                "destino",
                "msg_id",
                "delivered",
                "forward_util"
            ])
            writer.writerows(rows)

        print(f"[CSV] Convertido: {csv_file} ({len(rows)} linhas)")


# =========================
# 3. JUNTAR TODOS OS CSVs
# =========================
def merge_csvs():
    csv_files = glob.glob(os.path.join(CSV_DIR, "r*.csv"))
    dfs = []

    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        df["source_file"] = os.path.basename(csv_file)
        dfs.append(df)

    if not dfs:
        print("[ERRO] Nenhum CSV encontrado para juntar.")
        return

    df_final = pd.concat(dfs, ignore_index=True)
    df_final.to_csv(FINAL_DATASET, index=False)

    print(f"[FINAL] Dataset salvo em {FINAL_DATASET}")
    print(f"[FINAL] Total de linhas: {len(df_final)}")

    print("\n[FINAL] Distribuicao de delivered:")
    print(df_final["delivered"].value_counts(dropna=False))

    print("\n[FINAL] Distribuicao de forward_util:")
    print(df_final["forward_util"].value_counts(dropna=False))

    print("\n[FINAL] Proporcao de forward_util:")
    print(df_final["forward_util"].value_counts(normalize=True))


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    cleanup_old_files()
    run_simulations()
    convert_txt_to_csv()
    merge_csvs()