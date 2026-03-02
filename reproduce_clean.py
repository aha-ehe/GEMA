import os

# Alamat/Offset untuk libmoba.so (ARM64)
OFFSETS = {
    'Signature_Check': 0x142a54, # pkcs7::get_from_apk
    'CRC_Bypass': 0xcca14,      # parseInput branch
    'IKCP_INTERVAL': 0x1c70d0,
    'IKCP_WND_SND': 0x1c70c0,
    'IKCP_MTU_DEF': 0x1c70c8
}

def create_clean_poc():
    source = 'libmoba.so'
    target = 'lib-moba-test.so'

    if not os.path.exists(source):
        print(f"Error: {source} tidak ditemukan!")
        return

    with open(source, 'rb') as f:
        data = bytearray(f.read())

    print(f"[*] Patching {source} (Versi: Clean-Boot Belut)...")

    # 1. Bypass Signature (Anti-Ban/Anti-Crash)
    # Patch pkcs7::get_from_apk agar selalu mengembalikan success (1)
    data[OFFSETS['Signature_Check']:OFFSETS['Signature_Check']+8] = bytes.fromhex('20008052c0035fd6')

    # 2. Bypass Integritas CRC (Silent modification)
    data[OFFSETS['CRC_Bypass']:OFFSETS['CRC_Bypass']+4] = bytes.fromhex('1f2003d5')

    # 3. Tuning Gerak (Ghosting)
    data[OFFSETS['IKCP_INTERVAL']:OFFSETS['IKCP_INTERVAL']+4] = (50).to_bytes(4, 'little')
    data[OFFSETS['IKCP_WND_SND']:OFFSETS['IKCP_WND_SND']+4] = (128).to_bytes(4, 'little')
    data[OFFSETS['IKCP_MTU_DEF']:OFFSETS['IKCP_MTU_DEF']+4] = (1400).to_bytes(4, 'little')

    with open(target, 'wb') as f:
        f.write(data)

    print(f"[+] Berhasil membuat {target}")
    print("[!] Fix: Masalah 'libmain.so not found' telah diatasi dengan bypass signature.")

if __name__ == "__main__":
    create_clean_poc()
