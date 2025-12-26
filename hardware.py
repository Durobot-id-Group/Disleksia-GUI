import serial
import serial.tools.list_ports
import threading
import time
import csv

# ================== EEG Serial ==================
class EEGSerialLogger:
    def __init__(self, port, baudrate=115200, out_csv="eeg_record.csv"):
        self.port = port
        self.baudrate = baudrate
        self.out_csv = out_csv
        self.running = False
        self.ser = None

    def start(self):
        if not serial: return
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)
            self.ser.reset_input_buffer()
            self.csv_file = open(self.out_csv, 'w', newline='')
            self.writer = csv.writer(self.csv_file)
            self.writer.writerow(["Timestamp", "ADC_KIRI", "ADC_KANAN"])
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
        except Exception as e:
            print("Serial error:", e)

    def _loop(self):
        start_time = time.time()
        while self.running and self.ser:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if ',' in line:
                        kiri, kanan = line.split(',')[:2]
                        ts = time.time() - start_time
                        self.writer.writerow([ts, int(kiri), int(kanan)])
            except:
                continue

    def stop(self):
        self.running = False
        time.sleep(0.1)
        try:
            if self.ser: self.ser.close()
            self.csv_file.close()
        except: pass
