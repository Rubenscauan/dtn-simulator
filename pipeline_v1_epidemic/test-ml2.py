# ml_step2_baseline.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.ensemble import RandomForestClassifier

# =========================
# 1. CARREGAR DADOS
# =========================
df = pd.read_csv("dataset_final.csv")

# transformar colunas categoricas em numeros
df["msg_num"] = df["msg_id"].astype("category").cat.codes
df["source_num"] = df["source_file"].astype("category").cat.codes

# alvo
y = df["forward_util"]

# features iniciais
X = df[["tempo", "origem", "destino", "msg_num", "source_num"]]

# =========================
# 2. DIVISAO TREINO / TESTE
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# =========================
# 3. BASELINE BURRO
# =========================
baseline_pred = [0] * len(y_test)

print("=== BASELINE (sempre 0) ===")
print("Accuracy:", accuracy_score(y_test, baseline_pred))
print("F1 classe 1:", f1_score(y_test, baseline_pred, zero_division=0))
print(classification_report(y_test, baseline_pred, zero_division=0))

# =========================
# 4. RANDOM FOREST INICIAL
# =========================
model = RandomForestClassifier(
    random_state=42,
    class_weight="balanced"
)

model.fit(X_train, y_train)
y_pred = model.predict(X_test)

print("\n=== RANDOM FOREST INICIAL ===")
print("Accuracy:", accuracy_score(y_test, y_pred))
print("F1 classe 1:", f1_score(y_test, y_pred, zero_division=0))
print(classification_report(y_test, y_pred, zero_division=0))