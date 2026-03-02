# Analisis Desync Logika (Logic Desync) - libmoba.so (Versi 3)

Strategi "belut" ini berfokus pada manipulasi frekuensi pengiriman perintah game (`Cmd_Battle_Move`) dengan tetap menjaga stabilitas jaringan lokal client.

## Strategi "Tuning 2x"

Berbeda dengan versi sebelumnya yang mencoba flooding agresif, versi ini meningkatkan responsivitas client sebesar 2x lipat dari standar:

| Fitur | Offset | Nilai | Tujuan |
|-------|--------|-------|--------|
| `IKCP_INTERVAL` | `0x1c70d0` | 50 (ms) | Mengirim perintah gerak 2x lebih sering. Di mata server, ini sering menyebabkan koreksi posisi yang "lembut" (sliding). |
| `IKCP_WND_SND` | `0x1c70c0` | 64 | Memberikan ruang lebih untuk batching `Cmd_Battle_Move`. |
| `IKCP_MTU_DEF` | `0x1c70c8` | 1400 | Menjamin paket tidak terfragmentasi secara lokal, sehingga ping tetap 8-10ms. |

## Mekanisme "Logic-Level Desync"

1. **Faster Command Flow:** Dengan `interval=50ms`, client meng-update state gerak lebih cepat daripada pemain standar (100ms). Hal ini memaksa server untuk memproses data dari kita lebih sering, yang bisa menyebabkan desinkronisasi pada pemain lain saat mencoba mengejar posisi kita.
2. **Artificial Jitter (Forced Zip):** Patch pada `KCP_IsZipEnabled` memaksa overhead pemrosesan paket. Gabungan antara pengiriman cepat dan pemrosesan yang sedikit lebih lama menciptakan profil trafik yang unik (elusive), yang sering kali melewati filter anti-cheat berbasis pola network yang kaku.
3. **No Local Stutter:** Dengan MTU tinggi dan interval yang tidak terlalu ekstrem, client tetap lancar tanpa visual lag (visual kejang).

## Status PoC

`lib-moba-test.so` v3 telah dibuat dengan parameter tuning ini untuk memberikan keunggulan responsivitas halus sekaligus menciptakan tantangan sinkronisasi bagi lawan di dalam pertandingan.
