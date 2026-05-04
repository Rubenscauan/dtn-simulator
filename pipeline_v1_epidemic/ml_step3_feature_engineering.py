import pandas as pd

# =========================
# 1. CARREGAR DADOS
# =========================
df = pd.read_csv("dataset_final.csv")

# transformar categorias em numeros
df["msg_num"] = df["msg_id"].astype("category").cat.codes
df["source_num"] = df["source_file"].astype("category").cat.codes

# ordenar corretamente
df = df.sort_values(["source_file", "tempo"]).reset_index(drop=True)

# =========================
# 2. FEATURES DE HISTORICO
# =========================

# quantas vezes a mensagem já foi encaminhada
df["msg_forward_count_before"] = (
    df.groupby(["source_file", "msg_id"]).cumcount()
)

# quantas vezes origem já encaminhou
df["origem_forward_count_before"] = (
    df.groupby(["source_file", "origem"]).cumcount()
)

# quantas vezes destino já recebeu algo
df["destino_receive_count_before"] = (
    df.groupby(["source_file", "destino"]).cumcount()
)

# quantas vezes esse par apareceu
df["pair_count_before"] = (
    df.groupby(["source_file", "origem", "destino"]).cumcount()
)

# idade da mensagem
first_msg_time = df.groupby(["source_file", "msg_id"])["tempo"].transform("min")
df["msg_age"] = df["tempo"] - first_msg_time

# quantos nós diferentes já receberam a msg
def unique_receivers_before(group):
    seen = set()
    result = []
    for d in group:
        result.append(len(seen))
        seen.add(d)
    return result

df["unique_receivers_before"] = (
    df.groupby(["source_file", "msg_id"])["destino"]
    .transform(lambda x: pd.Series(unique_receivers_before(x), index=x.index))
)

# =========================
# 3. SALVAR
# =========================
df.to_csv("dataset_features.csv", index=False)

print("Arquivo criado: dataset_features.csv")
print(df.head())