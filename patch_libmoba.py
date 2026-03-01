import os

def patch():
    if not os.path.exists('libmoba.so'):
        print("Error: libmoba.so not found!")
        return

    with open('libmoba.so', 'rb') as f:
        data = bytearray(f.read())

    # --- Network Patches (Server Stress) ---
    # IKCP_MTU_DEF at 0x1c70c8: Set to 50
    data[0x1c70c8:0x1c70cc] = (50).to_bytes(4, 'little')
    # IKCP_RTO_MIN at 0x1c709c: Set to 10
    data[0x1c709c:0x1c70a0] = (10).to_bytes(4, 'little')
    # IKCP_RTO_NDL at 0x1c7098: Set to 10
    data[0x1c7098:0x1c709c] = (10).to_bytes(4, 'little')
    # IKCP_INTERVAL at 0x1c70d0: Set to 10
    data[0x1c70d0:0x1c70d4] = (10).to_bytes(4, 'little')

    # --- Logic/Zip Patches ---
    # Force KCP_IsZipEnabled (0xca7b0) and KCP_EnableZip (0xca7a0) to return 1 (True)
    # ARM64: MOV W0, #1; RET -> 20 00 80 52 C0 03 5F D6
    patch_bytes = bytes.fromhex('20008052c0035fd6')
    data[0xca7b0:0xca7b8] = patch_bytes
    data[0xca7a0:0xca7a8] = patch_bytes

    # Change g_iZipControlCode at 0x1c7088 to 1
    data[0x1c7088:0x1c708c] = (1).to_bytes(4, 'little')

    with open('lib-moba-test.so', 'wb') as f:
        f.write(data)

    print("Successfully created lib-moba-test.so with server-stress patches.")

if __name__ == "__main__":
    patch()
