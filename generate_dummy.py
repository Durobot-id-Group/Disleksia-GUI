import numpy as np
import pandas as pd
import time

def generate_eeg_csv(filename="dummy_eeg.csv", duration_sec=60, fs=256, condition="dyslexia"):
    """
    Membuat file CSV dummy dengan sinyal sintetis.
    
    Parameters:
    - filename: Nama file output
    - duration_sec: Durasi rekaman dalam detik
    - fs: Sampling rate (Hz)
    - condition: 'normal' atau 'dyslexia'
    """
    
    print(f"Sedang men-generate data '{condition}' selama {duration_sec} detik...")
    
    # 1. Buat sumbu waktu
    num_samples = duration_sec * fs
    t = np.linspace(0, duration_sec, num_samples)
    
    # 2. Fungsi pembantu untuk membuat gelombang sinus
    def create_wave(freq, amplitude):
        return amplitude * np.sin(2 * np.pi * freq * t)

    # 3. Komposisi Sinyal Berdasarkan Kondisi
    # Inisialisasi sinyal dasar (noise)
    noise = np.random.normal(0, 10, num_samples) # Random noise
    
    if condition == "dyslexia":
        # Skenario Disleksia: Delta Tinggi, Gamma Rendah
        # Delta (0.5 - 4 Hz) -> KITA BUAT KUAT
        s_delta = create_wave(2.0, 80)  
        # Theta (4 - 8 Hz)
        s_theta = create_wave(6.0, 20)
        # Alpha (8 - 13 Hz)
        s_alpha = create_wave(10.0, 10)
        # Beta (13 - 30 Hz)
        s_beta = create_wave(20.0, 15)
        # Gamma (30 - 45 Hz) -> KITA BUAT LEMAH
        s_gamma = create_wave(40.0, 2) 
        
    else: # Normal / Rileks
        # Skenario Normal: Alpha Dominan (Mata tertutup/Rileks)
        # Delta
        s_delta = create_wave(2.0, 10)
        # Theta
        s_theta = create_wave(6.0, 10)
        # Alpha -> KITA BUAT KUAT
        s_alpha = create_wave(10.0, 60)
        # Beta
        s_beta = create_wave(20.0, 15)
        # Gamma
        s_gamma = create_wave(40.0, 10)

    # Gabungkan semua gelombang
    raw_signal_uv = s_delta + s_theta + s_alpha + s_beta + s_gamma + noise

    # 4. Konversi ke ADC Value (Simulasi Hardware)
    # Asumsi: VREF 1.65V (tengah-tengah 3.3V), Gain 1000
    # ADC range 0-4095. Nilai tengah kira-kira 2048.
    # Kita balik rumus: ADC = (uV * Gain / 1e6 + VREF) / 3.3 * 4095
    
    GAIN = 1000.0
    VREF = 1.65
    
    # Channel Kiri (Utama)
    voltage_kiri = (raw_signal_uv * 1e-6 * GAIN) + VREF
    adc_kiri = (voltage_kiri / 3.3) * 4095
    
    # Channel Kanan (Buat sedikit berbeda/asimetris)
    raw_signal_kanan = raw_signal_uv * 0.9 + np.random.normal(0, 5, num_samples)
    voltage_kanan = (raw_signal_kanan * 1e-6 * GAIN) + VREF
    adc_kanan = (voltage_kanan / 3.3) * 4095

    # Clip agar tidak keluar range 0-4095 (hardware limits)
    adc_kiri = np.clip(adc_kiri, 0, 4095).astype(int)
    adc_kanan = np.clip(adc_kanan, 0, 4095).astype(int)

    # 5. Simpan ke CSV
    df = pd.DataFrame({
        "Timestamp": t,
        "ADC_KIRI": adc_kiri,
        "ADC_KANAN": adc_kanan
    })
    
    df.to_csv(filename, index=False)
    print(f"SUKSES! File tersimpan: {filename}")
    print("-" * 30)

# ================== MENU PILIHAN ==================
if __name__ == "__main__":
    print("GENERATOR DATA EEG DUMMY")
    print("1. Buat data simulasi DISLEKSIA (Delta Tinggi)")
    print("2. Buat data simulasi NORMAL (Alpha Dominan)")
    
    pilihan = input("Pilih (1/2): ")
    
    if pilihan == "1":
        generate_eeg_csv("dummy_disleksia.csv", condition="dyslexia")
    elif pilihan == "2":
        generate_eeg_csv("dummy_normal.csv", condition="normal")
    else:
        print("Pilihan salah, membuat default (dyslexia)...")
        generate_eeg_csv("dummy_test.csv", condition="dyslexia")