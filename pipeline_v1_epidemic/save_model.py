# save_model.py

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

df = pd.read_csv("dataset_features.csv")

feature_cols = [
    "tempo",
    "origem",
    "destino",
    "msg_num",
    "source_num",
    "msg_forward_count_before",
    "origem_forward_count_before",
    "destino_receive_count_before",
    "pair_count_before",
    "msg_age",
    "unique_receivers_before",
]

X = df[feature_cols]
y = df["forward_util"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = RandomForestClassifier(
    random_state=42,
    class_weight="balanced"
)
model.fit(X_train, y_train)

joblib.dump(model, "ml_router_model.pkl")
joblib.dump(feature_cols, "ml_router_features.pkl")

print("Modelo salvo em ml_router_model.pkl")
print("Features salvas em ml_router_features.pkl")