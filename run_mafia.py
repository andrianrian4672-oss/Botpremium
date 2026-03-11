import threading
import os
import subprocess
import sys
import time

# Daftar 5 Tuyul VIP Bos (Sesuai urutan txt)
BOTS = [
    {"name": "Peaxel_Max", "api_env": "API_KEY_MAX", "priv_env": "PRIV_KEY_MAX"},
    {"name": "Peaxel_Lite", "api_env": "API_KEY_LITE", "priv_env": "PRIV_KEY_LITE"},
    {"name": "Peaxel_Dex", "api_env": "API_KEY_DEX", "priv_env": "PRIV_KEY_DEX"},
    {"name": "Peaxel_Turbo", "api_env": "API_KEY_TURBO", "priv_env": "PRIV_KEY_TURBO"},
    {"name": "Peaxel_Solar", "api_env": "API_KEY_SOLAR", "priv_env": "PRIV_KEY_SOLAR"},
]

def run_bot(bot_name, api_key, private_key):
    # Duplikat environment Railway, lalu timpa dengan data masing-masing bot
    env = os.environ.copy()
    env["BOT_NAME"] = bot_name
    env["API_KEY"] = api_key
    env["PRIVATE_KEY"] = private_key
    
    # Menjalankan botpremium.py
    subprocess.run([sys.executable, "botpremium.py"], env=env)

if __name__ == "__main__":
    print("="*50)
    print("🎩 MEMBANGUNKAN 5 KARTEL PEAXEL VIP DI RAILWAY 🎩")
    print("="*50)
    
    threads = []
    
    for bot in BOTS:
        api_key = os.environ.get(bot["api_env"], "")
        private_key = os.environ.get(bot["priv_env"], "")
        
        if api_key and private_key:
            print(f"🚀 Menyiapkan senjata & tiket VIP untuk {bot['name']}...")
            t = threading.Thread(target=run_bot, args=(bot['name'], api_key, private_key))
            t.start()
            threads.append(t)
            time.sleep(3) # Jeda 3 detik per bot biar server gamenya nggak kaget
        else:
            print(f"⚠️ {bot['name']} ditahan! {bot['api_env']} atau {bot['priv_env']} kosong di Variables Railway.")
            
    # Tunggu sampai semua pertempuran selesai
    for t in threads:
        t.join()
        
    print("\n🛑 Semua operasi tempur VIP selesai.")
    print("💤 Masuk mode HIBERNASI selamanya agar Railway tidak menyedot tiket 2x...")
    while True:
        time.sleep(86400)