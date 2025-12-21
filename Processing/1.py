import numpy as np
import pandas as pd

def deteksi_disleksia(
    data,
    sampling_rate,
    segment_duration=10,
    threshold=50,
    indikasi_ratio=0.7
):
    """
    data              : array 1D / Series EEG
    sampling_rate     : Hz (contoh 256)
    segment_duration  : durasi tiap kelompok (detik)
    threshold         : nilai ambang batas
    indikasi_ratio    : rasio minimal segmen terindikasi
    """

    data = np.array(data)
    samples_per_segment = sampling_rate * segment_duration

    # Jumlah segmen
    total_segments = len(data) // samples_per_segment
    if total_segments == 0:
        raise ValueError("Data terlalu pendek untuk dibagi menjadi segmen")

    indikasi = 0

    for i in range(total_segments):
        start = i * samples_per_segment
        end = start + samples_per_segment
        segment = data[start:end]

        # Contoh fitur: rata-rata nilai absolut
        feature_value = np.mean(np.abs(segment))

        if feature_value > threshold:
            indikasi += 1

    rasio_indikasi = indikasi / total_segments

    if rasio_indikasi >= indikasi_ratio:
        hasil = "disleksia"
    else:
        hasil = "tidak disleksia"

    return {
        "total_segmen": total_segments,
        "segmen_terindikasi": indikasi,
        "rasio": rasio_indikasi,
        "hasil": hasil
    }

df = pd.read_csv("Deteksi Disleksia 16 Agustus 2024.csv")

hasil = deteksi_disleksia(
    data=df["latitude"],
    sampling_rate=10,
    segment_duration=10,
    threshold=10
)

print(hasil)
