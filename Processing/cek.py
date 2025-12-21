import pandas as pd


df = pd.read_csv("Deteksi Disleksia 16 Agustus 2024.csv")

panjang = len(df["latitude"])

print(panjang)