import glob
import pandas as pd

dfs = []

for file in glob.glob("r*.csv"):
    dfs.append(pd.read_csv(file))

df_final = pd.concat(dfs, ignore_index=True)
df_final.to_csv("dataset_final.csv", index=False)