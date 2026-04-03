import requests
import threading
import queue
import re
import os

# --- KONFIGURASI ---
THREADS = 100 # Menaikkan thread agar lebih cepat untuk interval menit
TIMEOUT = 10 
TEST_URL = "http://httpbin.org/get?show_env=1"

SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/proxy.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/Bes-js/public-proxy-list/refs/heads/main/proxies.txt",
    "https://raw.githubusercontent.com/vmheaven/VMHeaven-Free-Proxy-Updated/refs/heads/main/all_proxies.txt",
    "https://raw.githubusercontent.com/r00tee/Proxy-List/refs/heads/main/Socks4.txt",
    "https://raw.githubusercontent.com/r00tee/Proxy-List/refs/heads/main/Socks5.txt",
    "https://raw.githubusercontent.com/stormsia/proxy-list/refs/heads/main/working_proxies.txt",
    "https://raw.githubusercontent.com/dpangestuw/Free-Proxy/refs/heads/main/All_proxies.txt",
    "https://raw.githubusercontent.com/databay-labs/free-proxy-list/refs/heads/master/socks5.txt",
    "https://raw.githubusercontent.com/databay-labs/free-proxy-list/refs/heads/master/http.txt",
    "https://raw.githubusercontent.com/MrMarble/proxy-list/refs/heads/main/all.txt",
    "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/http.txt",
    "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/https.txt",
    "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/refs/heads/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/iplocate/free-proxy-list/refs/heads/main/all-proxies.txt",
    "https://raw.githubusercontent.com/krokmazagaga/http-proxy-list/refs/heads/main/http.txt",
    "https://raw.githubusercontent.com/VPSLabCloud/VPSLab-Free-Proxy-List/refs/heads/main/all_proxies.txt",
    "https://raw.githubusercontent.com/Mohammedcha/ProxRipper/refs/heads/main/full_proxies/http.txt",
    "https://raw.githubusercontent.com/Mohammedcha/ProxRipper/refs/heads/main/full_proxies/https.txt",
    "https://raw.githubusercontent.com/Mohammedcha/ProxRipper/refs/heads/main/full_proxies/socks4.txt",
    "https://raw.githubusercontent.com/Mohammedcha/ProxRipper/refs/heads/main/full_proxies/socks5.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/all/data.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/refs/heads/master/proxies.txt"
]

results = {"all": [], "http": [], "socks4": [], "socks5": []}
countries = {}
q = queue.Queue()

def get_anon(res_json, my_ip):
    origin = res_json.get('origin', '')
    if my_ip and my_ip in origin: return "Transparent"
    return "Elite" if not res_json.get('headers', {}).get('Via') else "Anonymous"

def worker(my_ip):
    while not q.empty():
        proxy = q.get()
        # Coba deteksi protokol secara bergantian
        for proto in ['http', 'socks4', 'socks5']:
            try:
                px = {"http": f"{proto}://{proxy}", "https": f"{proto}://{proxy}"}
                r = requests.get(TEST_URL, proxies=px, timeout=TIMEOUT)
                if r.status_code == 200:
                    ip_only = proxy.split(':')[0]
                    # Ambil data negara (ip-api)
                    try:
                        c_data = requests.get(f"http://ip-api.com/json/{ip_only}", timeout=5).json()
                        cc = c_data.get('countryCode', 'UN')
                    except: cc = "UN"
                    
                    anon = get_anon(r.json(), my_ip)
                    full_proxy = f"{proto}://{proxy}"
                    
                    results["all"].append(f"{proxy} | {proto.upper()} | {cc} | {anon}")
                    results[proto].append(proxy)
                    
                    if cc not in countries: countries[cc] = []
                    countries[cc].append(full_proxy)
                    break # Berhenti jika sudah ketemu protokol yang cocok
            except: continue
        q.task_done()

def main():
    # Buat folder jika belum ada
    if not os.path.exists('results/countries'): os.makedirs('results/countries', exist_ok=True)
    
    try: my_ip = requests.get("https://api.ipify.org").text
    except: my_ip = None

    print("--- Memulai Pengumpulan Proxy ---")
    raw = []
    for s in SOURCES:
        try:
            res = requests.get(s, timeout=15)
            found = re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', res.text)
            raw.extend(found)
            print(f"Sumber {s[:30]}... Berhasil")
        except: pass

    unique_list = list(set(raw))
    print(f"Total unik ditemukan: {len(unique_list)}. Menjalankan pengecekan...")

    for p in unique_list: q.put(p)
    
    for _ in range(THREADS):
        threading.Thread(target=worker, args=(my_ip,), daemon=True).start()
    q.join()

    # Menyimpan file ke folder results/
    for k, v in results.items():
        with open(f"results/{k}.txt", "w") as f: f.write("\n".join(v))
    
    for cc, v in countries.items():
        with open(f"results/countries/{cc}.txt", "w") as f: f.write("\n".join(v))

    print("--- Selesai. Data Tersimpan ---")

if __name__ == "__main__":
    main()
