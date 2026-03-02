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
    'Battle_Move_Visit': 0xe1bb8
}

def create_poc_v3():
    source = 'libmoba.so'
    target = 'lib-moba-test.so'

    if not os.path.exists(source):
        print(f"Error: {source} tidak ditemukan!")
        return

    with open(source, 'rb') as f:
        data = bytearray(f.read())

    print(f"[*] Memulai patching {source} (Versi 3: Logic Desync)...")

    # 1. MTU Stabil (1400) - Agar ping tetap hijau (8-10ms)
    data[OFFSETS['IKCP_MTU_DEF']:OFFSETS['IKCP_MTU_DEF']+4] = (1400).to_bytes(4, 'little')

    # 2. Window Size Menengah (64) - Agar tidak overload tapi tetap menampung banyak Cmd_Udp_Data
    data[OFFSETS['IKCP_WND_SND']:OFFSETS['IKCP_WND_SND']+4] = (64).to_bytes(4, 'little')
    data[OFFSETS['IKCP_WND_RCV']:OFFSETS['IKCP_WND_RCV']+4] = (64).to_bytes(4, 'little')

    # 3. Interval Cepat (50ms) - Mempercepat pengiriman Cmd_Battle_Move dibanding client standar
    # (Default 100ms -> 50ms = 2x lebih responsif/cepat di mata server)
    data[OFFSETS['IKCP_INTERVAL']:OFFSETS['IKCP_INTERVAL']+4] = (50).to_bytes(4, 'little')

    # 4. Patch Logic Zip (Force Compression) - Menambah jitter alami
    # ARM64: MOV W0, #1; RET -> 20 00 80 52 C0 03 5F D6
    patch_zip = bytes.fromhex('20008052c0035fd6')
    data[OFFSETS['KCP_IsZipEnabled']:OFFSETS['KCP_IsZipEnabled']+8] = patch_zip
    data[OFFSETS['KCP_EnableZip']:OFFSETS['KCP_EnableZip']+8] = patch_zip

    with open(target, 'wb') as f:
        f.write(data)

    print(f"[+] Berhasil membuat {target} (Strategy: Logic Desync)")
    print("[!] Gunakan file ini untuk desinkronisasi halus tanpa stuttering visual.")

if __name__ == "__main__":
    create_poc_v3()
