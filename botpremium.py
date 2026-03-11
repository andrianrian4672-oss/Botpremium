import requests
import time
import sys
import random
import os
import json
import re
from eth_account import Account

# ================== KONFIGURASI AMAN (RAILWAY MODE) ==================
BASE_URL = "https://cdn.moltyroyale.com/api"

# 🔥 NGAMBIL DATA DARI ENVIRONMENT VARIABLES RAILWAY 🔥
API_KEY = os.environ.get("API_KEY", "KOSONG")
BOT_NAME = os.environ.get("BOT_NAME", "Bot_Tanpa_Nama")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "KOSONG")

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

TURN_DELAY = 60  

# ================== SISTEM MEMORI & RECOVERY ==================
safe_bot_name = re.sub(r'[^a-zA-Z0-9_]', '', BOT_NAME)
SESSION_FILE = f"session_VIP_{safe_bot_name}.json"

def load_session():
    # 1. Coba baca dari file lokal (kalau masih ada)
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                if data.get("game_id") and data.get("agent_id"):
                    return data.get("game_id"), data.get("agent_id")
        except Exception:
            pass

    # 2. JALUR DARURAT (RECOVERY NYANGKUT)
    try:
        print(f"🔍 [{BOT_NAME}] Mengecek riwayat game VIP yang sedang berjalan di server...")
        res = requests.get(f"{BASE_URL}/accounts/me", headers=HEADERS, timeout=10).json()
        
        if res.get("success"):
            current_games = res.get("data", {}).get("currentGames", [])
            for g in current_games:
                # Cari game PAID/PREMIUM yang statusnya belum selesai
                if g.get("entryType") in ["paid", "premium"] and g.get("gameStatus") in ["waiting", "running"]:
                    g_id = g.get("gameId")
                    a_id = g.get("agentId")
                    print(f"🚨 AHA! Ketemu Tuyul VIP lagi nunggu/main di Game: {g_id[-5:]}")
                    save_session(g_id, a_id) # Simpan paksa ke memori lokal
                    return g_id, a_id
    except Exception as e:
        print(f"⚠️ Gagal cek server recovery: {e}")

    return None, None

def save_session(game_id, agent_id):
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"game_id": game_id, "agent_id": agent_id}, f)
    except Exception:
        pass

def clear_session():
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception:
            pass

# ================== UTIL & LOGGER ==================
def fatal(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def get_waktu():
    return time.strftime('%H:%M:%S')

def smart_print(bot_memory, text):
    if bot_memory.get("last_log_msg") != text:
        print(f"[{get_waktu()}] {text}")
        bot_memory["last_log_msg"] = text

# ================== API HANDLERS (KHUSUS PREMIUM) ==================
def get_waiting_premium_game():
    MAX_PERCOBAAN = 10 
    print(f"🔍 [{get_waktu()}] [{BOT_NAME}] Radar VIP Aktif! Mencari room BERBAYAR (PAID/PREMIUM)...")
    url = f"{BASE_URL}/games?status=waiting"
    
    for attempt in range(1, MAX_PERCOBAAN + 1):
        try:
            response = requests.get(url, timeout=10)
            res = response.json()
            
            if res.get("success") and res.get("data"):
                for game in reversed(res["data"]):
                    status_game = game.get("status", "").lower()
                    entry_type = game.get("entryType", "").lower()
                    
                    # 🔥 RADAR UDAH BISA BACA LABEL 'PREMIUM' 🔥
                    if status_game == "waiting" and entry_type in ["paid", "premium"]:
                        print(f"✅ [{get_waktu()}] [{BOT_NAME}] Nemu Room VIP: {game.get('name')}")
                        return game["id"]
        except Exception as e:
            pass
            
        if attempt < MAX_PERCOBAAN:
            delay = random.uniform(2.0, 5.0)
            time.sleep(delay) 
            
    print(f"⚠️ [{get_waktu()}] [{BOT_NAME}] Room VIP kosong. Coba lagi nanti!")
    return None

def join_paid_game(game_id, private_key):
    print(f"🧾 [{BOT_NAME}] Meminta kontrak EIP-712 untuk Room VIP (Taruhan 100 $Moltz)...")
    try:
        # 1. Minta Pesan Kontrak dari Server
        res_msg = requests.get(f"{BASE_URL}/games/{game_id}/join-paid/message", headers=HEADERS).json()
        if not res_msg.get("success"):
            print(f"⚠️ Gagal dapat kontrak VIP: {res_msg.get('error', {}).get('message', res_msg)}")
            return None
        
        eip712_data = res_msg["data"]
        deadline = eip712_data["message"]["deadline"]
        
        # 2. Tanda Tangani Kontrak pakai Private Key (Web3)
        print(f"✍️ [{BOT_NAME}] Menandatangani transaksi Web3...")
        account = Account.from_key(private_key)
        signed_message = account.sign_typed_data(full_message=eip712_data)
        
        # 🔥 FIX 0x SIGNATURE 🔥
        signature = "0x" + signed_message.signature.hex() 
        
        # 3. Serahkan Tanda Tangan ke Server
        payload = {
            "deadline": str(deadline),
            "signature": signature
        }
        res_join = requests.post(f"{BASE_URL}/games/{game_id}/join-paid", headers=HEADERS, json=payload).json()
        
        if not res_join.get("success"):
            pesan_error = res_join.get("error", {}).get("message", "Misterius")
            print(f"⚠️ DITOLAK MASUK VIP: {pesan_error}")
            print("💡 TIP: Pastikan saldo $Moltz cukup dan agen sudah di-Whitelist oleh Owner di web!")
            return None
            
        agent_id = res_join["data"]["agentId"]
        tx_hash = res_join["data"].get("txHash", "0x...")
        print(f"✅ [{BOT_NAME}] BERHASIL BAYAR TIKET! Masuk VIP (ID: {agent_id})")
        print(f"🔗 TxHash: {tx_hash}")
        return agent_id
        
    except Exception as e:
        print(f"⚠️ Error proses Web3: {e}")
        return None

def start_game(game_id):
    requests.post(f"{BASE_URL}/games/{game_id}/start", headers=HEADERS)

def get_state(game_id, agent_id):
    try:
        res_raw = requests.get(f"{BASE_URL}/games/{game_id}/agents/{agent_id}/state", headers=HEADERS, timeout=10)
        if res_raw.status_code in [400, 403, 404]: return "MATI"
        res = res_raw.json()
        if not res.get("success"): return "MATI"
        return res.get("data")
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None

def send_action(game_id, agent_id, action_payload):
    try:
        if "action" not in action_payload: payload = {"action": action_payload}
        else: payload = action_payload
        res = requests.post(f"{BASE_URL}/games/{game_id}/agents/{agent_id}/action", headers=HEADERS, json=payload, timeout=10).json()
        return res
    except Exception as e:
        return None

# ================== FUNGSI DETEKSI BARANG ==================
def cari_barang_di_tanah(state, region):
    items = state.get("visibleItems", [])
    if not items: items = region.get("items", [])
    if not items: items = state.get("items", [])
    if not items: items = state.get("droppedItems", [])
    return items

def ekstrak_info_item(item_data):
    if isinstance(item_data, (str, int)): return str(item_data), "Barang Misterius"
    elif isinstance(item_data, dict):
        item_id = item_data.get("id") or item_data.get("_id") or item_data.get("itemId") or item_data.get("uid")
        item_name = item_data.get("name") or item_data.get("typeId") or "Loot"
        if "item" in item_data and isinstance(item_data["item"], dict):
            data_asli = item_data["item"]
            if not item_name or item_name == "Loot": item_name = data_asli.get("name") or data_asli.get("typeId") or "Barang"
            if not item_id: item_id = data_asli.get("id")
        if not item_id:
            for key, val in item_data.items():
                if isinstance(val, str) and len(val) > 10 and key not in ["name", "type", "description", "regionId"]:
                    item_id = val
                    break
        return str(item_id), str(item_name)
    return None, None

def is_valid_weapon(item_name, item_data):
    name_lower = str(item_name).lower()
    blacklist = ["fist", "none", "bandage", "medkit", "ration", "potion", "moltz", "coin", "emergency", "megaphone", "radio", "map"]
    for word in blacklist:
        if word in name_lower: return False
    if isinstance(item_data, dict):
        i_data = item_data.get("item", item_data)
        if isinstance(i_data, dict):
            item_type = str(i_data.get("type", "")).lower()
            if item_type != "" and "weapon" not in item_type: return False
    if any(w in name_lower for w in ["sniper", "rifle", "katana", "pistol", "gun", "sword", "bow", "knife", "dagger"]): return True
    return False

def get_weapon_score(weapon_name):
    name_lower = str(weapon_name).lower()
    if "fist" in name_lower or "none" in name_lower: return 0
    if "sniper" in name_lower or "rifle" in name_lower: return 60
    if "katana" in name_lower: return 50
    if "pistol" in name_lower or "gun" in name_lower: return 40
    if "sword" in name_lower: return 30
    if "bow" in name_lower: return 20
    if "knife" in name_lower or "dagger" in name_lower: return 10
    return 5 

def sort_loot_priority(item_data):
    _, name = ekstrak_info_item(item_data)
    nl = str(name).lower()
    if "moltz" in nl or "coin" in nl: return 999  
    if "medkit" in nl or "bandage" in nl or "emergency" in nl: return 100 
    if "sniper" in nl or "katana" in nl or "rifle" in nl: return 80 
    if "ration" in nl or "potion" in nl: return 50
    return 10

# ================== AI LOGIC (OTAK SUPER PEAXEL) ==================
def cari_pintu_strategis(pintu_aman, region_dict, hp_sekarat):
    if not pintu_aman: return None
    ruins = []
    forests = []
    others = []
    for r_id in pintu_aman:
        region_data = region_dict.get(str(r_id).lower(), {})
        terrain = str(region_data.get('terrain', '')).lower()
        if 'ruins' in terrain: ruins.append(r_id)
        elif 'forest' in terrain: forests.append(r_id)
        else: others.append(r_id)
    if hp_sekarat and len(forests) > 0: return random.choice(forests)
    if not hp_sekarat and len(ruins) > 0: return random.choice(ruins)
    return random.choice(pintu_aman)

def bungkus_aksi(aksi_dict, reasoning="Mengamankan area.", planned="Bertahan hidup di arena VIP."):
    return {
        "action": aksi_dict,
        "thought": {"reasoning": reasoning, "plannedAction": planned}
    }

def decide_action(state, bot_memory):
    self_data = state.get("self", {})
    try: my_hp_val = int(self_data.get("hp", 100))
    except: my_hp_val = 100
    try: my_ep_val = int(self_data.get("ep", 10))
    except: my_ep_val = 10
        
    my_id = self_data.get("id")
    region = state.get("currentRegion", {})
    current_region_id = region.get("id")
    visible_regions = state.get("visibleRegions", [])
    
    adjacent_regions = state.get("connectedRegions") or region.get("connections") or state.get("visibleRegions") or []
    adjacent_ids = [str(r.get("id") if isinstance(r, dict) else r).lower() for r in adjacent_regions]
    
    region_dict = {}
    for r in visible_regions + state.get("connectedRegions", []) + [region]:
        if isinstance(r, dict):
            r_id = str(r.get("id", "")).lower()
            if r_id: region_dict[r_id] = r

    if "dz_memory" not in bot_memory: bot_memory["dz_memory"] = set()
    if "pdz_memory" not in bot_memory: bot_memory["pdz_memory"] = set()
    if "sampah_memory" not in bot_memory: bot_memory["sampah_memory"] = set()
    if "last_hp" not in bot_memory: bot_memory["last_hp"] = 100

    hp_loss = bot_memory["last_hp"] - my_hp_val
    bot_memory["last_hp"] = my_hp_val

    if current_region_id != bot_memory.get("last_region_id"):
        bot_memory["taunted_agents"] = set()
        bot_memory["last_region_id"] = current_region_id

    game_data = state.get("game", {})
    raw_pdz = state.get("pendingDeathzones", []) + state.get("pendingDeathZones", []) + game_data.get("pendingDeathzones", [])
    raw_dz = state.get("deathzones", []) + state.get("deathZones", []) + game_data.get("deathzones", [])

    for pdz in raw_pdz: bot_memory["pdz_memory"].add(str(pdz.get("id", pdz)).lower())
    for dz in raw_dz: bot_memory["dz_memory"].add(str(dz.get("id", dz)).lower())

    current_r_id = str(current_region_id).lower()
    current_r_name = str(region.get("name", "")).lower()
    
    is_death_zone_now = current_r_id in bot_memory["dz_memory"] or current_r_name in bot_memory["dz_memory"] or region.get("isDeathZone", False)
    is_pending_dz_now = current_r_id in bot_memory["pdz_memory"] or current_r_name in bot_memory["pdz_memory"] or region.get("isPendingDeathZone", False)
        
    interactables = region.get("interactables", [])
    id_medical = None
    id_supply = None
    
    for fac in interactables:
        if not fac.get("isUsed"):  
            fac_name = str(fac.get("name", "")).lower()
            fac_id = fac.get("id")
            if "medical" in fac_name: id_medical = fac_id
            elif "supply" in fac_name: id_supply = fac_id
            
    inventory = self_data.get("inventory", [])
    id_potion = None
    id_bandage = None
    tangan_kosong = True
    equipped_w_score = 0
    equipped_w_name = "Tangan Kosong"
    weapon_range = 0
    best_inv_w_id = None
    best_inv_w_name = None
    best_inv_w_score = -1
    
    punya_megaphone = False
    punya_radio = False
    punya_map = False
    
    equipped_item = self_data.get("equippedWeapon") or self_data.get("weapon")
    if equipped_item:
        _, equipped_w_name_raw = ekstrak_info_item(equipped_item)
        nm_low = equipped_w_name_raw.lower()
        if "fist" in nm_low or "none" in nm_low:
            tangan_kosong = True
            equipped_w_score = 0
        else:
            tangan_kosong = False
            equipped_w_name = equipped_w_name_raw
            equipped_w_score = get_weapon_score(equipped_w_name_raw)
            if any(w in nm_low for w in ["bow", "pistol", "sniper", "rifle", "gun"]): weapon_range = 1

    for item in inventory:
        is_equipped = isinstance(item, dict) and item.get("isEquipped", False)
        item_id, item_name = ekstrak_info_item(item)
        name_lower = str(item_name).lower()
        
        if "megaphone" in name_lower: punya_megaphone = True
        if "radio" in name_lower: punya_radio = True
        if "map" in name_lower: punya_map = True
        
        if is_equipped:
            if "fist" in name_lower or "none" in name_lower:
                tangan_kosong = True
                equipped_w_score = 0
            else:
                tangan_kosong = False
                equipped_w_name = item_name
                equipped_w_score = get_weapon_score(item_name)
                if any(w in name_lower for w in ["bow", "pistol", "sniper", "rifle", "gun"]): weapon_range = 1
            continue

        if "bandage" in name_lower or "medkit" in name_lower or "emergency" in name_lower:
            if not id_bandage: id_bandage = item_id 
        elif "ration" in name_lower or "potion" in name_lower:
            if not id_potion: id_potion = item_id 
            
        if is_valid_weapon(item_name, item):
            score = get_weapon_score(item_name)
            if score > best_inv_w_score:
                best_inv_w_score = score
                best_inv_w_id = item_id
                best_inv_w_name = item_name

    musuh_player = []
    musuh_monster = []
    teman_player = []
    
    semua_orang = state.get("visibleAgents", []) + state.get("visibleNpcs", []) + state.get("visibleMonsters", []) + state.get("monsters", []) + region.get("npcs", []) + region.get("monsters", [])
    
    for a in semua_orang:
        if a.get("isAlive", True) and a.get("id") != my_id:
            m_reg_id = str(a.get("regionId")).lower()
            jarak_ke_musuh = 0 if m_reg_id == current_r_id else (1 if m_reg_id in adjacent_ids else 99)
            
            if jarak_ke_musuh <= max(weapon_range, 1):
                a['jarak'] = jarak_ke_musuh
                is_monster = "type" in a and a["type"] in ["monster", "npc"] or any(m in str(a.get("name", "")).lower() for m in ["wolf", "bear", "bandit"])
                
                if "peaxel" in str(a.get("name", "")).lower(): teman_player.append(a)
                elif is_monster: musuh_monster.append(a)
                else: musuh_player.append(a)

    musuh_player.sort(key=lambda x: x.get("hp", 100))
    musuh_monster.sort(key=lambda x: x.get("hp", 100))
    
    musuh_player_terlemah = musuh_player[0] if len(musuh_player) > 0 else None
    musuh_monster_terlemah = musuh_monster[0] if len(musuh_monster) > 0 else None
        
    musuh_player_sekamar = [m for m in musuh_player if m.get("jarak") == 0]
    jumlah_pengeroyok = len(musuh_player_sekamar)
    
    teman_sekamar = [t for t in teman_player if t.get("jarak") == 0]
    kekuatan_tim = 1 + len(teman_sekamar)

    barang_di_area = cari_barang_di_tanah(state, region)
    barang_di_area.sort(key=sort_loot_priority, reverse=True)

    # ================== KOMUNIKASI MAFIA (BACOT & HT) ==================
    if jumlah_pengeroyok > 0 and bot_memory.get("last_talk_region") != current_region_id:
        bot_memory["last_talk_region"] = current_region_id
        bacotan = random.choice([
            "VIP Room ini milik Kartel Peaxel! Minggir lo semua!",
            "Yang bukan keluarga Peaxel, mending cabut sebelum rata!",
            "Nyawa kalian cuma senilai 100 Moltz di mataku!"
        ])
        smart_print(bot_memory, f"[{BOT_NAME}] 💬 BACOT VIP: {bacotan}")
        return bungkus_aksi({"type": "talk", "message": bacotan}, "Intimidasi psikologis.", "Menjatuhkan mental musuh VIP.")

    if my_hp_val < 50 and (time.time() - bot_memory.get("last_whisper_time", 0)) > 300: 
        teman_kelihatan = [t for t in teman_player if t.get("id") != my_id]
        if teman_kelihatan:
            teman_target = random.choice(teman_kelihatan)
            bot_memory["last_whisper_time"] = time.time()
            pesan = f"Bro, gue di {current_r_name} (HP:{my_hp_val}). Butuh back-up segera!"
            smart_print(bot_memory, f"[{BOT_NAME}] 📻 HT ke {teman_target.get('name')}: {pesan}")
            return bungkus_aksi({"type": "whisper", "targetId": teman_target.get("id"), "message": pesan}, "Kondisi terdesak.", "Meminta bala bantuan dari keluarga Kartel.")

    # ================== DAFTAR FUNGSI AKSI ==================
    def aksi_move(pesan_kustom="🚪 Melipir cari aman...", wajib_aman=False, target_pasti=None, reasoning="Bergerak taktis.", planned="Mencari posisi menguntungkan."):
        if my_ep_val < 1: 
            smart_print(bot_memory, f"[{BOT_NAME}] 💤 EP Habis! Terpaksa tidur dulu (Rest)!")
            return bungkus_aksi({"type": "rest"}, "Kelelahan ekstrem (EP habis).", "Istirahat untuk memulihkan stamina.")
            
        if target_pasti and target_pasti in adjacent_ids:
            smart_print(bot_memory, f"[{BOT_NAME}] 🏃 {pesan_kustom}")
            return bungkus_aksi({"type": "move", "regionId": target_pasti}, reasoning, planned)

        if not adjacent_regions: return None 
            
        pintu_aman = []
        pintu_blind = []
        pintu_pending = []
        
        for r in adjacent_regions:
            raw_id = r.get("id") if isinstance(r, dict) else r
            if not raw_id: continue
                
            r_id = str(raw_id).lower()
            r_obj = region_dict.get(r_id, {})
            
            is_dz = r_id in bot_memory["dz_memory"] or r_obj.get("isDeathZone") or r_obj.get("isDeathzone")
            is_pdz = r_id in bot_memory["pdz_memory"] or r_obj.get("isPendingDeathZone") or r_obj.get("isPendingDeathzone")
            
            if not is_dz: 
                if is_pdz: pintu_pending.append(raw_id)
                elif r_obj: pintu_aman.append(raw_id)
                else: pintu_blind.append(raw_id)
                
        target_id = None
        
        if len(pintu_aman) > 0:
            pilihan_baru = [r for r in pintu_aman if r not in bot_memory["visited_path"]]
            if len(pilihan_baru) > 0: 
                target_id = cari_pintu_strategis(pilihan_baru, region_dict, my_hp_val < 60)
            else: 
                ruangan_sebelumnya = bot_memory["visited_path"][-1] if len(bot_memory["visited_path"]) > 0 else None
                pilihan_darurat = [r for r in pintu_aman if r != ruangan_sebelumnya]
                target_id = cari_pintu_strategis(pilihan_darurat if len(pilihan_darurat) > 0 else pintu_aman, region_dict, my_hp_val < 60)
                
            smart_print(bot_memory, f"[{BOT_NAME}] 🏃 {pesan_kustom}")
        elif not wajib_aman:
            if len(pintu_blind) > 0:
                target_id = random.choice(pintu_blind)
                smart_print(bot_memory, f"[{BOT_NAME}] 🏃 {pesan_kustom} (Pintu Gelap)")
            elif len(pintu_pending) > 0:
                target_id = random.choice(pintu_pending)
                smart_print(bot_memory, f"[{BOT_NAME}] 🏃 {pesan_kustom} (Pintu Pending DZ)")

        if target_id:
            if target_id in bot_memory["visited_path"]: 
                bot_memory["visited_path"].remove(target_id)
            bot_memory["visited_path"].append(target_id)
            if len(bot_memory["visited_path"]) > 20: 
                bot_memory["visited_path"].pop(0)
            return bungkus_aksi({"type": "move", "regionId": target_id}, reasoning, planned)
        return None 
        
    def aksi_serang(target_id, target_type, reasoning="Target terdeteksi.", planned="Eksekusi tanpa ampun."): 
        if my_ep_val < 2:
            smart_print(bot_memory, f"[{BOT_NAME}] 💤 EP cuma {my_ep_val}! Istirahat (Rest) ambil napas buat nyerang!")
            return bungkus_aksi({"type": "rest"}, "Napas habis sebelum mengeksekusi.", "Mengambil napas untuk pukulan mematikan.")
        return bungkus_aksi({"type": "attack", "targetId": target_id, "targetType": target_type}, reasoning, planned)

    def aksi_pungut(item_data, reasoning="Menemukan barang berharga.", planned="Mengamankan aset untuk modal menang."): 
        item_id, _ = ekstrak_info_item(item_data)
        return bungkus_aksi({"type": "pickup", "itemId": item_id}, reasoning, planned)

    def aksi_pakai_item(item_id, reasoning="Kondisi HP kritis.", planned="Melakukan penyembuhan instan."): 
        if my_ep_val < 1: return bungkus_aksi({"type": "rest"}, "Sangat lelah untuk memakai item.", "Istirahat sejenak.")
        return bungkus_aksi({"type": "use_item", "itemId": item_id}, reasoning, planned)

    def aksi_equip(item_id, reasoning="Ada senjata yang lebih sakit.", planned="Memasang perlengkapan tempur maksimal."): 
        return bungkus_aksi({"type": "equip", "itemId": item_id}, reasoning, planned)

    def aksi_interact(fasilitas_id, reasoning="Menemukan fasilitas pendukung.", planned="Mengeksploitasi fasilitas untuk keuntungan."): 
        if my_ep_val < 1: return bungkus_aksi({"type": "rest"}, "Butuh tenaga.", "Istirahat sebentar.")
        return bungkus_aksi({"type": "interact", "interactableId": fasilitas_id}, reasoning, planned)

    def aksi_buang(item_id, pesan_kustom="Membuang barang...", reasoning="Manajemen tas.", planned="Membuang barang usang untuk efisiensi."): 
        smart_print(bot_memory, f"[{BOT_NAME}] 🗑️ {pesan_kustom}")
        return bungkus_aksi({"type": "drop", "itemId": item_id}, reasoning, planned)

    # ================== INSTING KILAT ==================
    if best_inv_w_id:
        if tangan_kosong or best_inv_w_score > equipped_w_score:
            smart_print(bot_memory, f"[{BOT_NAME}] ✨ UPGRADE SENJATA VIP! Pakai [{best_inv_w_name}]!")
            return aksi_equip(best_inv_w_id)

    # 🔥 AUTO-CLEAN (SMART INVENTORY) ANTI LOAK 🔥
    skor_maksimal_kita = max(equipped_w_score, best_inv_w_score)
    for item in inventory:
        is_eq = isinstance(item, dict) and item.get("isEquipped", False)
        if not is_eq:
            i_id, i_name = ekstrak_info_item(item)
            if i_id in bot_memory["sampah_memory"]: continue 
            
            if is_valid_weapon(i_name, item):
                skor_tas = get_weapon_score(i_name)
                if skor_tas <= skor_maksimal_kita:
                    bot_memory["sampah_memory"].add(i_id) 
                    return aksi_buang(i_id, f"AUTO-CLEAN: Buang {i_name} usang (Sudah pegang yg lebih bagus)!")

    # ================== REFLEKS ANTI-SAMSAK ==================
    if hp_loss > 0 and jumlah_pengeroyok == 0:
        sniper = None
        for m in musuh_player:
            if m.get("jarak") == 1:
                sniper = m
                break
        if sniper and weapon_range == 0: 
            if my_hp_val > 60:
                smart_print(bot_memory, f"[{BOT_NAME}] 😡 DITEMBAK DARI JAUH! MAJU TABRAK {sniper.get('name')}!")
                aksi = aksi_move("Nyerbu lokasi penembak!", target_pasti=str(sniper.get("regionId")).lower(), reasoning="Diserang Sniper.", planned="Maju frontal balasan.")
                if aksi: return aksi
            else:
                smart_print(bot_memory, f"[{BOT_NAME}] 😱 DITEMBAK SILUMAN! LARI!!!")
                aksi = aksi_move("Menghindari tembakan!", wajib_aman=True, reasoning="Darah bocor dari jauh.", planned="Mencari cover dan kabur.")
                if aksi: return aksi
        elif not sniper:
            smart_print(bot_memory, f"[{BOT_NAME}] 👻 DITEMBAK GAIB! LARI KABUR!")
            aksi = aksi_move("Menghindari hantu sniper!", wajib_aman=True, reasoning="Ancaman tak terlihat.", planned="Kabur dari area berbahaya.")
            if aksi: return aksi

    # ================== PUNGUT BARANG ==================
    if len(barang_di_area) > 0:
        if tangan_kosong:
            for b in barang_di_area:
                bid, bnm = ekstrak_info_item(b)
                if is_valid_weapon(bnm, b):
                    smart_print(bot_memory, f"[{BOT_NAME}] 🚨 DARURAT SENJATA VIP! Sikat {bnm}!")
                    return aksi_pungut(b, "Butuh senjata darurat.", "Menghindari mati konyol di VIP dengan tangan kosong.")

        for item_terbaik in barang_di_area:
            _, nama_barang = ekstrak_info_item(item_terbaik)
            nm_low = nama_barang.lower()
            
            if "megaphone" in nm_low and punya_megaphone: continue
            if "radio" in nm_low and punya_radio: continue
            if "map" in nm_low and punya_map: continue
                
            if is_valid_weapon(nama_barang, item_terbaik):
                skor_barang_ini = get_weapon_score(nama_barang)
                if skor_barang_ini <= skor_maksimal_kita: continue
            
            tas_penuh = True if len(inventory) >= 10 else False
            is_koin = True if "moltz" in nm_low or "coin" in nm_low else False
            
            if is_koin:
                smart_print(bot_memory, f"[{BOT_NAME}] 💰 MATA DUITAN VIP! Ada {nama_barang}, SIKAT!")
                return aksi_pungut(item_terbaik, "Melihat harta karun Koin.", "Sikat untuk balik modal tiket VIP.")
            
            if not tas_penuh:
                smart_print(bot_memory, f"[{BOT_NAME}] 🎒 Ambil Barang VIP: {nama_barang}!")
                return aksi_pungut(item_terbaik)

    # ================== CEK COOLDOWN ==================
    sisa_cd = bot_memory.get("group1_cd_end", 0) - time.time()
    if sisa_cd > 0: return {"type": "WAITING_CD"}

    # ================== SURVIVAL & HEALING DEWA ==================
    is_trapped_in_dz = False
    if is_death_zone_now or is_pending_dz_now:
        aksi_lari = aksi_move("🚨 ZONA MERAH/BAHAYA VIP! Evakuasi Segera!", wajib_aman=True, reasoning="Zona kematian terdeteksi.", planned="Evakuasi secepatnya menyelamatkan tiket VIP.")
        if aksi_lari: return aksi_lari
        else: is_trapped_in_dz = True

    batas_heal = 95 if is_trapped_in_dz else 80 
    if my_hp_val < batas_heal:
        if id_medical:
            smart_print(bot_memory, f"[{BOT_NAME}] 🏥 Pakai Medical Facility VIP!")
            return aksi_interact(id_medical, "HP menipis dan ada RS.", "Berobat jalan agar bertahan hidup.")
        elif id_bandage:
            smart_print(bot_memory, f"[{BOT_NAME}] 🚑 Suntik Obat VIP! (HP:{my_hp_val})")
            return aksi_pakai_item(id_bandage)
        elif id_potion:
            smart_print(bot_memory, f"[{BOT_NAME}] 🚑 Minum Potion VIP! (HP:{my_hp_val})")
            return aksi_pakai_item(id_potion)

    # 🔥 PROTOKOL MENTAL BAJA (ANTI BUNUH DIRI) 🔥
    if jumlah_pengeroyok >= 3 and jumlah_pengeroyok > kekuatan_tim:
        aksi = aksi_move(f"🚨 Musuh {jumlah_pengeroyok} orang, geng kita cuma {kekuatan_tim}. KABURRR!", wajib_aman=True, reasoning="Dikeroyok musuh paus VIP.", planned="Mundur untuk atur ulang formasi.")
        if aksi: return aksi
        else: smart_print(bot_memory, f"[{BOT_NAME}] 🛑 ZONA AKHIR VIP BUNTU! TAWURAN SINI KAU!")

    if jumlah_pengeroyok >= 2 and jumlah_pengeroyok > kekuatan_tim and my_hp_val < 75:
        aksi = aksi_move(f"🚨 Kalah jumlah geng & HP Bocor! Mundur taktis dulu!", wajib_aman=True, reasoning="HP kritis dan kalah jumlah.", planned="Menghindar dari mati konyol.")
        if aksi: return aksi

    # 🔥 SMART COMBAT LOGIC VIP (NINJA ASSASSIN) 🔥
    if musuh_player_terlemah:
        target = musuh_player_terlemah
        hp_musuh = target.get("hp", 100)
        nama_musuh = target.get("name", "Player")
        jarak_musuh = target.get("jarak", 0)
        target_region = target.get("regionId")
        
        if tangan_kosong:
            aksi = aksi_move("Tangan kosong! Melarikan diri cari senjata VIP...", wajib_aman=True, reasoning="Nekat tangan kosong = hilang 100 Moltz.", planned="Mencari senjata sebelum membalas.")
            if aksi: return aksi
            return aksi_serang(target.get("id"), "agent", "Terpojok di VIP.", "Berjuang pakai tinju kosong.")

        if jarak_musuh == 0:
            if len(teman_sekamar) > 0:
                smart_print(bot_memory, f"[{BOT_NAME}] 🤝 GANKING VIP! Bantu saudara hajar {nama_musuh}!")
                return aksi_serang(target.get("id"), "agent", "Menemukan saudara seperjuangan.", "Keroyok musuh VIP bersama Kartel.")
            elif hp_musuh <= 40:
                smart_print(bot_memory, f"[{BOT_NAME}] 🦅 VULTURE MODE! Nyampah kill VIP {nama_musuh} (HP:{hp_musuh})!")
                return aksi_serang(target.get("id"), "agent", "Musuh VIP lengah dan sekarat.", "Menyelesaikan penderitaannya.")
            elif my_hp_val > 85 or hp_musuh <= my_hp_val:
                smart_print(bot_memory, f"[{BOT_NAME}] ⚔️ Eksekusi Taruhan: {nama_musuh} (HP:{hp_musuh})!")
                return aksi_serang(target.get("id"), "agent", "Adu mekanik VIP.", "Percaya diri bisa memenangkan duel berbayar.")
            else:
                aksi = aksi_move(f"⚠️ {nama_musuh} lebih sehat (HP:{hp_musuh}). Melipir ah, main aman!", wajib_aman=True, reasoning="Lawan VIP lebih tebal HP-nya.", planned="Bermain pintar menjaga aset.")
                if aksi: return aksi
                smart_print(bot_memory, f"[{BOT_NAME}] ⚔️ Mentok! Terpaksa duel mati-matian lawan {nama_musuh} di VIP!")
                return aksi_serang(target.get("id"), "agent", "Terpojok tanpa pintu keluar.", "Duel titik darah penghabisan untuk 8000 Moltz.")

        elif jarak_musuh > 0:
            if weapon_range > 0:
                smart_print(bot_memory, f"[{BOT_NAME}] 🎯 SNIPER VIP! Tembak {nama_musuh} dari jauh!")
                return aksi_serang(target.get("id"), "agent", "Pegang senjata jauh.", "Memanfaatkan jarak untuk cicil HP lawan.")
            else:
                if hp_musuh <= 30 and my_hp_val > 70:
                    smart_print(bot_memory, f"[{BOT_NAME}] 🏃‍♂️ Kejar {nama_musuh} yg lagi sekarat!")
                    return aksi_move("Kejar musuh VIP sekarat", target_pasti=str(target_region).lower(), reasoning="Paus sekarat kabur.", planned="Kejar dan buru sampai dapat loot premiumnya.")

    # 🔥 PREMAN PASAR (BARBAR FARMING MONSTER) 🔥
    if musuh_monster_terlemah:
        target = musuh_monster_terlemah
        nama_musuh = target.get("name", "Monster")
        jarak_musuh = target.get("jarak", 0)
        target_region = target.get("regionId")
        
        if my_hp_val > 60 and jumlah_pengeroyok == 0 and not is_death_zone_now and not is_pending_dz_now:
            if jarak_musuh == 0:
                smart_print(bot_memory, f"[{BOT_NAME}] 🥊 PREMAN PASAR! Bantai {nama_musuh}!")
                return aksi_serang(target.get("id"), "monster", "Ruangan sepi dari player lain.", "Farming monster buat cari Koin modal.")
            elif jarak_musuh > 0 and weapon_range == 0:
                smart_print(bot_memory, f"[{BOT_NAME}] 🏃‍♂️ Samperin {nama_musuh} buat dipalak!")
                return aksi_move("Maju ke ruangan monster", target_pasti=str(target_region).lower(), reasoning="Ada monster di kamar sebelah.", planned="Samperin dan jadikan tambang koin.")
            elif jarak_musuh > 0 and weapon_range > 0:
                smart_print(bot_memory, f"[{BOT_NAME}] 🎯 Tembak {nama_musuh} buat farming!")
                return aksi_serang(target.get("id"), "monster", "Punya senjata jauh aman.", "Tembak monster dari aman.")

    if id_supply:
        smart_print(bot_memory, f"[{BOT_NAME}] 📦 Maling kotak Supply Cache VIP!")
        return aksi_interact(id_supply, "Nemu Supply Cache gratis.", "Eksploitasi untuk modal looting VIP.")

    aksi_akhir = aksi_move("🕵️ Patroli cari duit & tempat aman VIP...", reasoning="Area sepi.", planned="Explore dan mencari loot sisa.")
    if aksi_akhir: return aksi_akhir
    
    if my_ep_val < 1: return bungkus_aksi({"type": "rest"}, "Energi Terkuras.", "Menunggu stamina pulih.")
    return bungkus_aksi({"type": "explore"}, "Tidak ada jalan keluar.", "Mencari celah barang di lantai VIP.")

# ================== RADAR & LAPORAN ==================
def print_live_status(state, game_id):
    self_data = state.get("self", {})
    region = state.get("currentRegion", {})
    hp = self_data.get('hp', '?')
    ep = self_data.get('ep', '?') 
    tas = len(self_data.get('inventory', []))
    loc = region.get('name', '?')
    
    senjata_info = "Tangan Kosong 👊"
    equipped_item = self_data.get("equippedWeapon") or self_data.get("weapon")
    if equipped_item:
        _, nm = ekstrak_info_item(equipped_item)
        if "fist" not in nm.lower() and "none" not in nm.lower(): senjata_info = f"{nm} 🗡️"
            
    print(f"\n[💎 GAME VIP {game_id[-5:]}] [{BOT_NAME}] | HP:{hp} | EP:{ep} | Tas:{tas}/10 | Senj: {senjata_info} | Lokasi:{loc}")

def cetak_laporan_kemenangan(state):
    self_data = state.get("self", {})
    hp_akhir = self_data.get("hp", "?")
    inventory = self_data.get("inventory", [])
    print("\n" + "💎"*25)
    print("  🎉🔥 JACKPOT VIP! 8000 MOLTZ + 160 CROSS! 🔥🎉")
    print("💎"*25)
    print(f"  👑 Sultan : {BOT_NAME.upper()}")
    print(f"  ❤️ Sisa HP: {hp_akhir}/100")
    print("==================================================\n")

def cetak_laporan_forensik(bot_memory, current_state):
    print("\n" + "="*50)
    print(f"💀 LAPORAN FORENSIK KEMATIAN VIP (MOLTZ HANGUS) 💀")
    print("="*50)
    
    state_sumber = current_state if isinstance(current_state, dict) else bot_memory.get("last_state", {})
    if not state_sumber: return
        
    self_data = state_sumber.get("self", {})
    region = state_sumber.get("currentRegion", {})
    
    if "killerName" in self_data or "killer" in self_data:
        print(f"🩸 Tersangka: {self_data.get('killerName', self_data.get('killer', 'Unknown'))}")
    print(f"🕵️ TKP: {region.get('name', '?')}")
    print("="*50 + "\n")

# ================== MAIN PROCESS (ONE-SHOT) ==================
def main():
    if API_KEY == "KOSONG" or PRIVATE_KEY.startswith("0x_PRIVATE_KEY"): 
        fatal(f"[{BOT_NAME}] Konfigurasi belum diisi! Edit file bot_premium.py dulu!")
        
    game_id, agent_id = load_session()
    resume_berhasil = False
    
    if game_id and agent_id:
        print(f"🔄 [{get_waktu()}] [{BOT_NAME}] Sesi VIP ditemukan! Coba RECONNECT...")
        state = get_state(game_id, agent_id)
        
        if state and state != "MATI":
            is_alive = state.get("self", {}).get("isAlive", True)
            status_game = state.get("gameStatus", "").lower()
            
            if status_game not in ["finished", "cancelled"] and is_alive:
                print(f"✅ [{get_waktu()}] [{BOT_NAME}] RECONNECT BERHASIL! Masuk arena VIP...")
                resume_berhasil = True
            else:
                print(f"⚠️ [{get_waktu()}] [{BOT_NAME}] Game VIP sudah usai. Menghapus sesi...")
                clear_session()
        else:
            print(f"⚠️ [{get_waktu()}] [{BOT_NAME}] Room VIP kadaluarsa. Menghapus sesi...")
            clear_session()
            
    if not resume_berhasil:
        agent_id = None
        game_id = None
        
        while not agent_id:
            game_id = get_waiting_premium_game()
            if not game_id:
                time.sleep(5)
                continue
                
            # 🔥 JOIN PAID GAME (MEMBAYAR TIKET WEB3) 🔥
            agent_id = join_paid_game(game_id, PRIVATE_KEY)
            if not agent_id:
                time.sleep(3) 

        save_session(game_id, agent_id)
        start_game(game_id)
        print(f"⏳ [{get_waktu()}] [{BOT_NAME}] Menunggu VIP Battle dimulai...")
        
        while True:
            state = get_state(game_id, agent_id)
            if state == "MATI":
                print(f"❌ [{BOT_NAME}] Game keburu dihapus!")
                clear_session()
                return # Langsung Stop
                
            if state and state.get("gameStatus", "").lower() not in ["waiting", "created", "pending", ""]:
                print(f"🔥 [{get_waktu()}] [{BOT_NAME}] VIP MATCH DIMULAI! 🔥\n")
                break
            time.sleep(0.5) 

    bot_memory = {
        "visited_path": [], "dz_memory": set(), "pdz_memory": set(), "taunted_agents": set(),
        "sampah_memory": set(), "last_region_id": None, "last_state": None, "group1_cd_end": 0, 
        "last_print_time": 0, "last_log_msg": "", "last_hp": 100, "last_talk_region": None, "last_whisper_time": 0
    }

    while True:
        try:
            state = get_state(game_id, agent_id)
            if state == "MATI":
                cetak_laporan_forensik(bot_memory, state)
                clear_session()
                break # KELUAR DARI LOOP GAME
                
            if not state:
                time.sleep(1)
                continue
                
            bot_memory["last_state"] = state
            
            if not state.get("self", {}).get("isAlive"):
                cetak_laporan_forensik(bot_memory, state)
                clear_session()
                break # KELUAR DARI LOOP GAME
                
            if state.get("gameStatus") == "finished":
                if state.get("self", {}).get("isAlive"): cetak_laporan_kemenangan(state)
                else: print(f"\n🏁 [{get_waktu()}] [{BOT_NAME}] MATCH VIP SELESAI!")
                clear_session()
                break # KELUAR DARI LOOP GAME
            
            if time.time() - bot_memory["last_print_time"] >= 20:
                print_live_status(state, game_id)
                bot_memory["last_print_time"] = time.time()
                bot_memory["last_log_msg"] = "" 

            action_payload = decide_action(state, bot_memory)
            
            if action_payload:
                if action_payload.get("type") == "WAITING_CD":
                    time.sleep(1.5)
                    continue
                    
                act_type = action_payload.get("action", {}).get("type", "") if "action" in action_payload else action_payload.get("type", "")
                res = send_action(game_id, agent_id, action_payload)
                
                if res and res.get("success"):
                    if act_type in ["pickup", "equip", "talk", "whisper", "drop"]: time.sleep(0.2) 
                    else: 
                        bot_memory["group1_cd_end"] = time.time() + TURN_DELAY
                        time.sleep(1) 
                else: 
                    if res and "error" in res:
                        err_msg = res.get("error", {}).get("message", "Error nggak jelas")
                        if "cooldown" not in err_msg.lower(): print(f"⚠️ [{BOT_NAME}] Server VIP nolak aksi '{act_type}': {err_msg}")
                    time.sleep(1) 
            else: 
                time.sleep(1)
                
        except Exception:
            time.sleep(1)

# 🔥 PENTING: DIBIKIN AGAR HANYA JALAN 1 KALI (TIDAK LOOPING SETELAH MATI/MENANG) 🔥
if __name__ == "__main__":
    print("="*50)
    print("💎 MENYALAKAN MESIN SUPER PEAXEL VIP (ONE-SHOT MODE) 💎")
    print("="*50)
    try:
        main()
        print(f"🛑 [{BOT_NAME}] Operasi VIP selesai. Mesin bot dimatikan agar tiket tidak tersedot lagi.")
    except Exception as e:
        print(f"💥 [{BOT_NAME}] Crash sistem: {e}")
