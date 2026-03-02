# Analisis Eksploitasi "Belut" (Ghost Desync) - libmoba.so

Strategi ini berfokus pada bypass integritas paket dan manipulasi timing untuk menciptakan keunggulan kompetitif (Ghosting/Teleport) yang halus dan sulit dideteksi oleh sistem anti-cheat standar.

## Vektor Eksploitasi: Integrity Bypass & Timing Drift

Eksperimen sebelumnya gagal karena modifikasi kasar menyebabkan network stack client melakukan kompensasi berlebihan (stuttering). Strategi "Belut" ini bekerja pada layer logika yang lebih rendah:

| Komponen | Offset File | Patch (Hex) | Deskripsi |
|-----------|-------------|-------------|-----------|
| **CRC Bypass** | `0xcca14` | `1f 20 03 d5` | Mengganti `b.ne` (branch if not equal) dengan `NOP` pada pengecekan header CRC di `parseInput`. Hal ini memungkinkan modifikasi paket tanpa ditolak oleh sistem. |
| **Move Logic** | `0xa7c84` | `20 00 80 52 c0 03 5f d6` | Memastikan `NativeSupportMoveLogic` selalu aktif (`true`). Ini memberikan jalur eksekusi gerak yang lebih "langsung" ke KCP pipe. |
| **Speed Drift** | `0x1c70d0`| `32 00 00 00` | Mengubah interval update KCP dari 100ms ke 50ms. Client mengirim posisi 2x lebih sering, seringkali mendahului (ahead) pemain lain di mata server. |
| **Batch Window** | `0x1c70c0`| `80 00 00 00` | Memperbesar jendela pengiriman ke 128 (dari 32). Memberikan kapasitas buffer lebih besar untuk menampung lonjakan `Cmd_Battle_Move` tanpa packet drop. |

## Mekanisme "Ghosting" (Belut)

1. **Header Integrity Nullification:** Dengan membypass pengecekan CRC di `parseInput`, setiap paket yang datang (maupun yang keluar jika dipatch seimbang) akan dianggap valid. Ini adalah fondasi bagi modifikasi data lebih lanjut pada layer `SdpPacker`.
2. **Elastic Movement:** Karena interval update dipercepat (50ms) dan MTU tetap stabil (1400), client tetap memiliki ping hijau (8-10ms). Namun, karena pengiriman perintah gerak 2x lebih cepat, posisi client di server akan mengalami "drift" yang mengakibatkan efek teleportasi halus atau sliding bagi pemain lawan saat mencoba menyerang.
3. **Buffer Advantage:** Jendela 128 memungkinkan client untuk "menahan" (burst) paket data game dalam jumlah besar tanpa memicu mekanisme kontrol kongesti KCP (`nc=1` secara implisit), memberikan keuntungan responsivitas saat terjadi teamfight besar.

## Kesimpulan Analisis

Eksploitasi ini disebut "Belut" karena ia bekerja di bawah radar deteksi integritas paket standar. Ia tidak mencoba untuk "merusak" koneksi (DDoS/Flooding), melainkan "melunakkan" aturan sinkronisasi agar client memiliki keunggulan waktu dan posisi yang tidak terlihat oleh mata telanjang atau monitoring ping standar.
