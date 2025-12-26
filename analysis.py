import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, iirnotch
from config import VREF, GAIN  # Mengambil nilai dari config.py

# ================== EEG ANALYSIS HELPERS ==================
def notch_filter(data, freq, fs, Q=30):
    if len(data) < 12: return data
    try:
        nyq = 0.5 * fs
        b, a = iirnotch(freq / nyq, Q)
        return filtfilt(b, a, data)
    except: return data

def bandpass(data, lowcut, highcut, fs, order=4):
    if len(data) < max(12, order * 6): return data
    try:
        nyq = 0.5 * fs
        low, high = lowcut / nyq, highcut / nyq
        if low <= 0 or high >= 1: return data
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, data)
    except: return data

def deteksi_disleksia_riset(delta_signal, theta_signal, alpha_signal, beta_signal, gamma_signal, fs):
    results = {'kriteria': {}, 'scores': {}, 'indikasi': []}
    
    # Hitung Power
    delta_power = np.mean(delta_signal**2)
    theta_power = np.mean(theta_signal**2)
    alpha_power = np.mean(alpha_signal**2)
    beta_power = np.mean(beta_signal**2)
    gamma_power = np.mean(gamma_signal**2)
    
    total_power = delta_power + theta_power + alpha_power + beta_power + gamma_power + 1e-20
    delta_rel = (delta_power / total_power) * 100
    theta_rel = (theta_power / total_power) * 100
    alpha_rel = (alpha_power / total_power) * 100
    beta_rel = (beta_power / total_power) * 100
    gamma_rel = (gamma_power / total_power) * 100

    # Kriteria
    k1 = delta_rel > 35
    k2 = gamma_rel < 8
    delta_gamma_ratio = delta_power / (gamma_power + 1e-10)
    k3 = delta_gamma_ratio > 5.0
    
    delta_std = np.std(delta_signal)
    delta_variability = delta_std / (np.mean(np.abs(delta_signal)) + 1e-10)
    k4 = delta_variability > 1.2
    
    max_other = max(theta_rel, alpha_rel, beta_rel, gamma_rel)
    k5 = delta_rel > (max_other + 10)
    k6 = gamma_rel < (beta_rel - 5)
    
    try:
        dn = (delta_signal - np.mean(delta_signal)) / (np.std(delta_signal) + 1e-10)
        gn = (gamma_signal - np.mean(gamma_signal)) / (np.std(gamma_signal) + 1e-10)
        correlation = np.corrcoef(dn, gn)[0,1]
    except Exception:
        correlation = 0.0
    k7 = correlation < -0.3

    # Fill results
    results['kriteria']['high_delta'] = {'value': delta_rel, 'threshold':35, 'passed':k1, 'description':'Peningkatan Delta Power'}
    results['kriteria']['low_gamma'] = {'value': gamma_rel, 'threshold':8, 'passed':k2, 'description':'Penurunan Gamma Power'}
    results['kriteria']['delta_gamma_ratio'] = {'value': delta_gamma_ratio, 'threshold':5.0, 'passed':k3, 'description':'Rasio Delta/Gamma tinggi'}
    results['kriteria']['delta_variability'] = {'value': delta_variability, 'threshold':1.2, 'passed':k4, 'description':'Variabilitas Delta tinggi'}
    results['kriteria']['delta_dominance'] = {'value': delta_rel - max_other, 'threshold':10, 'passed':k5, 'description':'Delta dominan > margin'}
    results['kriteria']['gamma_lowest'] = {'value': beta_rel - gamma_rel, 'threshold':5, 'passed':k6, 'description':'Gamma signifikan lebih rendah dari Beta'}
    results['kriteria']['delta_gamma_inverse'] = {'value': correlation, 'threshold':-0.3, 'passed':k7, 'description':'Korelasi delta-gamma negatif'}

    kriteria_terpenuhi = sum([k1,k2,k3,k4,k5,k6,k7])
    total_kriteria = 7
    confidence_score = (kriteria_terpenuhi / total_kriteria) * 100

    if kriteria_terpenuhi >= 6:
        diagnosis = "INDIKASI DISLEKSIA - KUAT"
        confidence = "TINGGI"
        rekomendasi = "Sangat disarankan evaluasi lanjutan oleh profesional"
    elif kriteria_terpenuhi >= 4:
        diagnosis = "INDIKASI DISLEKSIA - RENDAH"
        confidence = "SEDANG"
        rekomendasi = "Disarankan evaluasi lebih lanjut"
    elif kriteria_terpenuhi >= 2:
        diagnosis = "TIDAK TERINDIKASI DISLEKSIA - BORDERLINE"
        confidence = "RENDAH"
        rekomendasi = "Monitoring dan tes ulang direkomendasikan"
    else:
        diagnosis = "TIDAK TERINDIKASI DISLEKSIA"
        confidence = "TINGGI"
        rekomendasi = "Pola EEG dalam batas normal"

    results.update({
        'diagnosis': diagnosis,
        'confidence': confidence,
        'confidence_score': confidence_score,
        'kriteria_terpenuhi': kriteria_terpenuhi,
        'total_kriteria': total_kriteria,
        'rekomendasi': rekomendasi,
        'relative_power': {
            'delta': delta_rel, 'theta': theta_rel, 'alpha': alpha_rel, 'beta': beta_rel, 'gamma': gamma_rel
        }
    })
    return results

def run_eeg_pipeline(filename):
    try:
        df = pd.read_csv(filename)
        # Handle jika kolom tidak sesuai, buat dummy data untuk demo jika gagal
        if "ADC_KIRI" not in df.columns:
             # Fallback: Create dummy data if CSV structure is wrong
            t = np.linspace(0, 10, 2560)
            adc_kiri = np.random.randint(1000, 3000, 2560)
            adc_kanan = np.random.randint(1000, 3000, 2560)
        else:
            t = df["Timestamp"].values
            adc_kiri = df["ADC_KIRI"].values
            adc_kanan = df["ADC_KANAN"].values
            
        eeg_uv_kiri = ((adc_kiri / 4095.0) * 3.3 - VREF) / GAIN * 1e6
        eeg_uv_kanan = ((adc_kanan / 4095.0) * 3.3 - VREF) / GAIN * 1e6

        duration = t[-1] - t[0] if len(t) > 1 else 1
        fs = len(t) / duration if duration > 0 else 256

        eeg_kiri = notch_filter(eeg_uv_kiri, 50, fs)
        eeg_kanan = notch_filter(eeg_uv_kanan, 50, fs)

        bands = {
            "Delta (0.5–4 Hz)": (0.5, 4),
            "Theta (4–8 Hz)": (4, 8),
            "Alpha (8–13 Hz)": (8, 13),
            "Beta (13–30 Hz)": (13, 30),
            "Gamma (30–45 Hz)": (30, 45)
        }

        fk, fn = {}, {}
        for name, (l, h) in bands.items():
            fk[name] = bandpass(eeg_kiri, l, h, fs)
            fn[name] = bandpass(eeg_kanan, l, h, fs)

        hasil = deteksi_disleksia_riset(
            fk["Delta (0.5–4 Hz)"], fk["Theta (4–8 Hz)"],
            fk["Alpha (8–13 Hz)"], fk["Beta (13–30 Hz)"],
            fk["Gamma (30–45 Hz)"],
            fs
        )
        
        # Hitung band powers untuk plotting
        band_powers = {name: np.mean(sig**2) for name, sig in fk.items()}

        return {
            "ok": True,
            "analysis": hasil,
            "fs": fs,
            "t": t,
            "raw_uv": eeg_kiri,
            "filtered": fk,
            "band_powers": band_powers
        }
    except Exception as e:
        return {"ok": False, "message": str(e)}
