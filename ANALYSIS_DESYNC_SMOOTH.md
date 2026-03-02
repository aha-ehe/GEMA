# Analisis Desync Halus (Smooth Desync) - libmoba.so

Strategi ini dirancang untuk menciptakan desinkronisasi antara client dan server tanpa memicu kenaikan ping yang drastis atau stuttering (kejang) pada visual client.

## Evolusi Strategi: Dari Flooding ke Tuning

Eksperimen sebelumnya menunjukkan bahwa modifikasi parameter ke nilai ekstrem (seperti MTU 50 atau Interval 1ms) menyebabkan network stack client kewalahan, yang berujung pada kenaikan ping lokal (8ms -> 250ms). Strategi baru ini menggunakan pendekatan "Tuning Halus":

| Parameter | Alamat | Nilai | Tujuan |
|-----------|--------|-------|--------|
| `IKCP_MTU_DEF` | `0x1c70c8` | 1400 | Menjaga paket tetap dalam ukuran standar Ethernet untuk menghindari fragmentasi lokal. |
| `IKCP_WND_SND` | `0x1c70c0` | 128 | Memperbesar antrian pengiriman agar lebih banyak perintah bisa "ditahan" atau dikirim bersamaan. |
| `IKCP_INTERVAL`| `0x1c70d0` | 100 | Menjaga frekuensi update tetap pada standar (100ms) agar indikator ping tetap hijau. |
| `IKCP_RTO_NDL` | `0x1c7098` | 20 | Mempercepat respon transmisi ulang tanpa menciptakan badai trafik. |

## Mekanisme "Smooth Desync"

1. **Window Buffering:** Dengan memperbesar jendela ke 128 (dari 32), client memiliki ruang lebih besar untuk menampung paket-paket `Cmd_Udp_Data` (seperti `Battle_Move`). Hal ini memungkinkan terjadinya lonjakan data yang sinkron tanpa memutus koneksi.
2. **Clock Awareness:** Analisis pada `KCP_GetMonotonicClockMS_C` menunjukkan bahwa sinkronisasi waktu sangat bergantung pada presisi milidetik. Tuning pada `IKCP_RTO_NDL` memengaruhi bagaimana KCP menghitung drift antara client dan server.
3. **Server Reconciliation Lag:** Dengan parameter ini, client tetap terlihat "sehat" oleh server (ping rendah), namun aliran data yang dikirim memiliki profil yang berbeda, yang memaksa logika rekonsiliasi posisi di server bekerja dalam mode prediksi (extrapolation) lebih sering.

## Status PoC

`lib-moba-test.so` telah diperbarui dengan parameter desinkronisasi halus ini untuk memberikan pengalaman bermain yang tetap lancar di sisi client namun memberikan tantangan sinkronisasi bagi server.
