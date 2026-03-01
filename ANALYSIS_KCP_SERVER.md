# Analisis Kerentanan Sisi Server - libmoba.so (Full Exploit Draft)

Analisis ini menggabungkan berbagai vektor serangan pada protokol KCP kustom untuk menciptakan beban maksimal pada server (match lag) tanpa membebani client secara berlebihan.

## Daftar Patch Terintegrasi

| Fitur | Parameter | Offset | Nilai | Dampak |
|-------|-----------|--------|-------|---------|
| **Network** | `IKCP_MTU_DEF` | `0x1c70c8` | 50 | Fragmentasi massal; 10-20x lebih banyak paket UDP per data game. |
| **Network** | `IKCP_RTO_MIN` | `0x1c709c` | 10 | Retransmission storm; server dipaksa kirim ulang data terus-menerus. |
| **Network** | `IKCP_INTERVAL`| `0x1c70d0` | 10 | Update loop dipercepat 10x lipat. |
| **Logic** | `KCP_IsZipEnabled` | `0xca7b0` | `true` | Memaksa server melakukan dekompresi pada setiap paket yang masuk. |
| **Logic** | `g_iZipControlCode` | `0x1c7088` | 1 | Mengubah parameter algoritma kompresi ke mode yang lebih berat. |

## Analisis Gabungan (Synergistic Attack)

Dengan menggabungkan fragmentasi ekstrem (MTU 50) dan pemaksaan kompresi (Zip), server akan mengalami dua jenis bottleneck secara bersamaan:
1. **I/O Bottleneck:** Karena jumlah paket yang masuk sangat banyak (akibat fragmentasi dan interval cepat).
2. **CPU Bottleneck:** Karena setiap dari ribuan paket tersebut harus melewati fungsi dekompresi (LZ4/Zlib) meskipun data aslinya mungkin tidak terkompresi dengan benar.

Kombinasi ini sangat efektif untuk menciptakan "Lag" yang dirasakan oleh seluruh pemain dalam satu pertandingan (match-wide lag) karena prosesor server terfokus melayani trafik anomali dari satu client ini.

## Status PoC

`lib-moba-test.so` telah diperbarui dengan seluruh rangkaian patch di atas untuk pengujian penetrasi dan analisis ketahanan infrastruktur server.
