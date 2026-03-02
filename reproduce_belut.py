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
    'CRC_Bypass_Branch': 0xcca14
}

def create_poc_belut():
    source = 'libmoba.so'
    target = 'lib-moba-test.so'

    if not os.path.exists(source):
        print(f"Error: {source} tidak ditemukan!")
        return

    with open(source, 'rb') as f:
        data = bytearray(f.read())

    print(f"[*] Memulai patching {source} (Strategy: Belut Ghost)...")

    # 1. Tuning Network (Belut Speed)
    data[OFFSETS['IKCP_MTU_DEF']:OFFSETS['IKCP_MTU_DEF']+4] = (1400).to_bytes(4, 'little')
    data[OFFSETS['IKCP_INTERVAL']:OFFSETS['IKCP_INTERVAL']+4] = (50).to_bytes(4, 'little')
    data[OFFSETS['IKCP_WND_SND']:OFFSETS['IKCP_WND_SND']+4] = (128).to_bytes(4, 'little')
    data[OFFSETS['IKCP_WND_RCV']:OFFSETS['IKCP_WND_RCV']+4] = (128).to_bytes(4, 'little')

    # 2. Patch CRC Bypass (Integrity Nullification)
    # ARM64: NOP -> 1F 20 03 D5 (Mengganti B.NE)
    data[OFFSETS['CRC_Bypass_Branch']:OFFSETS['CRC_Bypass_Branch']+4] = bytes.fromhex('1f2003d5')

    # 3. Native Support Move (Always True)
    # ARM64: MOV W0, #1; RET -> 20 00 80 52 C0 03 5F D6
    patch_move = bytes.fromhex('20008052c0035fd6')
    data[OFFSETS['Native_Support_Move']:OFFSETS['Native_Support_Move']+8] = patch_move

    # 4. Patch Logic Zip (Natural Jitter)
    patch_zip = bytes.fromhex('20008052c0035fd6')
    data[OFFSETS['KCP_IsZipEnabled']:OFFSETS['KCP_IsZipEnabled']+8] = patch_zip
    data[OFFSETS['KCP_EnableZip']:OFFSETS['KCP_EnableZip']+8] = patch_zip

    with open(target, 'wb') as f:
        f.write(data)

    print(f"[+] Berhasil membuat {target} (Versi: Belut Ghost)")
    print("[!] CRC Bypass & Ghost Movement aktif. Gunakan untuk analisis mendalam.")

if __name__ == "__main__":
    create_poc_belut()
