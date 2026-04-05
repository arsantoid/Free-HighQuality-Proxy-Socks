import requests
import threading
import queue
import ipaddress
import os
import re
import random
import time

# --- KONFIGURASI HUNTER (MAKSIMAL & KETAT) ---
THREADS_SCAN = 150       # Power maksimal untuk GitHub Actions
TIMEOUT_SCAN = 3         # Standar ketat kamu tetap terjaga
TEST_URL_DETAIL = "http://httpbin.org/get?show_env=1"
TEST_URL_QUALITY = "https://www.google.com"

# Daftar Port Utuh Sesuai Milikmu
PORTS = [80, 8080, 3128, 1080, 8888, 7890, 9050, 5678]

hunted_results = []
q_scan = queue.Queue()
print_lock = threading.Lock()

# User-Agent Rotator (Anti-Detection)
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

def get_anon(res_json, my_ip):
    origin = res_json.get('origin', '')
    if my_ip and my_ip in origin: return "Transparent"
    return "Elite" if not res_json.get('headers', {}).get('Via') else "Anonymous"

def hunter_worker(my_ip):
    session = requests.Session()
    while not q_scan.empty():
        proxy = q_scan.get()
        # Mencoba dua protokol paling umum (HTTP & SOCKS5)
        for proto in ['http', 'socks5']:
            try:
                px = {"http": f"{proto}://{proxy}", "https": f"{proto}://{proxy}"}
                headers = {"User-Agent": random.choice(UA_LIST)}
                
                # Tahap 1: Validasi Anonimitas (Httpbin)
                r = session.get(TEST_URL_DETAIL, proxies=px, timeout=TIMEOUT_SCAN, headers=headers)
                if r.status_code == 200:
                    # Tahap 2: Validasi Kualitas (Google)
                    g = session.get(TEST_URL_QUALITY, proxies=px, timeout=5, headers=headers)
                    if g.status_code == 200:
                        ip_only = proxy.split(':')[0]
                        
                        # Tahap 3: Deteksi ISP & Negara (IP-API)
                        try:
                            geo_url = f"http://ip-api.com/json/{ip_only}?fields=status,countryCode,isp"
                            c_req = session.get(geo_url, timeout=5)
                            c_data = c_req.json()
                            
                            if c_data.get('status') == 'success':
                                cc = c_data.get('countryCode', 'UN')
                                isp = c_data.get('isp', 'Unknown ISP')
                                isp_name = (isp[:25] + '..') if len(isp) > 25 else isp
                            else:
                                cc, isp_name = "UN", "Private/Unknown"
                        except:
                            cc, isp_name = "UN", "Lookup Error"
                        
                        anon = get_anon(r.json(), my_ip)
                        # FORMAT FINAL: IP:PORT | PROTO | CC | ANON | ISP
                        result_entry = f"{proxy} | {proto.upper()} | {cc} | {anon} | {isp_name}"
                        
                        with print_lock:
                            print(f"[HUNTED SUCCESS] {result_entry}")
                        hunted_results.append(result_entry)
                        
                        time.sleep(1.2) # Jeda agar API ISP tidak nge-ban
                        break
            except:
                continue
        q_scan.task_done()

def main():
    output_dir = 'results/hunted'
    if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
    
    try: 
        my_ip = requests.get("https://api.ipify.org", timeout=10).text
    except: 
        my_ip = None

    if not os.path.exists('results/all.txt'):
        print("Data all.txt tidak ditemukan. Jalankan main.py dulu!")
        return

    print("--- MEMULAI PENYISIRAN MASIF (HYPER-COMBINATION NO LIMIT) ---")
    
    # 1. ANALISIS: Ambil SEMUA subnet unik dari hasil main.py
    block_subnets = set()
    with open('results/all.txt', 'r') as f:
        for line in f:
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                parts = match.group(1).split('.')
                # Ambil subnet /24 (tiga blok pertama)
                block_subnets.add(f"{parts[0]}.{parts[1]}.{parts[2]}")

    print(f"Ditemukan {len(block_subnets)} Subnet Potensial. Memulai raid total...")

    # 2. PENGISIAN ANTREAN: Sisir SELURUH IP tetangga (.1 sampai .254)
    for subnet in block_subnets:
        for d in range(1, 255):
            target_ip = f"{subnet}.{d}"
            # Kita hajar port-port paling potensial di tiap IP
            for port in [8080, 3128, 80]: 
                q_scan.put(f"{target_ip}:{port}")

    print(f"Total target pukat harimau: {q_scan.qsize()} kombinasi unik.")

    # 3. Eksekusi Hunter Threads
    for _ in range(THREADS_SCAN):
        threading.Thread(target=hunter_worker, args=(my_ip,), daemon=True).start()
    
    q_scan.join()

    # 4. SMART SAVE (Merge - Unique - Overwrite)
    if hunted_results:
        file_path = f"{output_dir}/hunted_elite.txt"
        
        # Baca data lama (jika ada)
        old_data = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                old_data = f.read().splitlines()
        
        # Gabungkan hasil lama + hasil baru hari ini
        merged_data = old_data + hunted_results
        
        # HAPUS DUPLIKAT (Gunakan set untuk filter unik)
        # Kita pakai set agar tidak ada IP yang sama tertulis dua kali
        unique_final = list(set(merged_data))
        
        # Tulis ulang semuanya ke file agar tetap bersih dan segar
        with open(file_path, "w") as f:
            f.write("\n".join(unique_final))
            
        print(f"--- DATABASE DIPERBARUI: Total {len(unique_final)} Proxy Unik (Baru: {len(hunted_results)}) ---")
    else:
        print("--- SELESAI: Belum ada proxy baru tertangkap hari ini. ---")

if __name__ == "__main__":
    main()
