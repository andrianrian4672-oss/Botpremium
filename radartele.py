import time
import requests
import os
from web3 import Web3

print("=============================================")
print(" 📡 RADAR TELEGRAM WEB3: PANTAU BRANKAS MOLTZ 📡")
print("=============================================")

# ================= KONFIGURASI =================
RPC_URL = "https://mainnet.crosstoken.io:22001"
PROXY_ADDRESS = "0x835fe0be30dfa4374071abb64b792c0c1c56da81"
TOKEN_ADDRESS = "0xdb99a97d607c5c5831263707E7b746312406ba7E"

# Ambil kunci dari brankas Railway biar aman!
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

CEK_INTERVAL = 60 # Cek brankas setiap 60 detik
# ===============================================

def kirim_telegram(pesan):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": pesan}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"⚠️ Gagal kirim Telegram: {e}")

# Koneksi ke Jalan Tol Web3
custom_provider = Web3.HTTPProvider(
    RPC_URL,
    request_kwargs={'headers': {'Content-Type': 'application/json'}, 'timeout': 30}
)
w3 = Web3(custom_provider)

proxy_addr = w3.to_checksum_address(PROXY_ADDRESS)
token_addr = w3.to_checksum_address(TOKEN_ADDRESS)

erc20_abi = [{
    "constant": True,
    "inputs": [{"name": "_owner", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"name": "balance", "type": "uint256"}],
    "type": "function"
}]

moltz_contract = w3.eth.contract(address=token_addr, abi=erc20_abi)

print("🚀 Menghidupkan Radar Telegram...")
kirim_telegram("🤖 Lapor Bos! Radar pemantau tuyul VIP di Railway sudah AKTIF dan siap memantau brankas 24 jam!")

saldo_terakhir = -1

while True:
    if not BOT_TOKEN:
        print("⚠️ Token Telegram kosong! Radar tidak bisa mengirim pesan.")
        time.sleep(60)
        continue

    try:
        raw_balance = moltz_contract.functions.balanceOf(proxy_addr).call()
        saldo_sekarang = float(w3.from_wei(raw_balance, 'ether'))

        if saldo_terakhir == -1:
            print(f"💰 Saldo Awal Brankas: {saldo_sekarang} MOLTZ")
            saldo_terakhir = saldo_sekarang
            
        elif saldo_sekarang > saldo_terakhir:
            cuan = saldo_sekarang - saldo_terakhir
            pesan = (
                f"🎉🎉 BOOYAH! VIP JACKPOT! 🎉🎉\n\n"
                f"📈 Setoran Masuk: +{cuan} MOLTZ\n"
                f"🏦 Total Brankas: {saldo_sekarang} MOLTZ\n\n"
                f"🔥 Gas terus Operasi Monopoli Bosku!"
            )
            print("Pesan terkirim ke Telegram!")
            kirim_telegram(pesan)
            saldo_terakhir = saldo_sekarang
            
        elif saldo_sekarang < saldo_terakhir:
            pesan_wd = f"💸 Penarikan/Potongan sukses! Saldo sisa: {saldo_sekarang} MOLTZ"
            kirim_telegram(pesan_wd)
            saldo_terakhir = saldo_sekarang

    except Exception as e:
        print(f"Lagi ngelag baca Blockchain... santai dulu.")

    time.sleep(CEK_INTERVAL)