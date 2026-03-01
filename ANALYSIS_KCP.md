# Analisis Protokol KCP pada libmoba.so

Analisis ini dilakukan untuk mengidentifikasi parameter dan logika dalam implementasi KCP kustom pada `libmoba.so` yang dapat dimodifikasi untuk menyebabkan masalah performa (lag) selama pertandingan.

## Temuan Parameter KCP

Berdasarkan analisis simbol dan data pada `libmoba.so` (versi ARM64), ditemukan konstanta global berikut yang mengontrol perilaku protokol KCP:

| Parameter | Alamat Virtual (VA) | Offset File | Nilai Default | Dampak Modifikasi |
|-----------|-------------------|-------------|---------------|-------------------|
| `IKCP_INTERVAL` | `0x1cf0d0` | `0x1c70d0` | 100 (ms) | Mengontrol frekuensi pembaruan internal KCP. Menurunkan nilai ini (misal ke 1ms) akan menyebabkan banjir paket (flooding). |
| `IKCP_WND_SND` | `0x1cf0c0` | `0x1c70c0` | 32 | Ukuran jendela pengiriman. Memperbesar nilai ini secara ekstrem meningkatkan penggunaan memori buffer. |
| `IKCP_WND_RCV` | `0x1cf0c4` | `0x1c70c4` | 32 | Ukuran jendela penerimaan. Sama seperti di atas, meningkatkan alokasi sumber daya. |
| `IKCP_RTO_DEF` | `0x1cf0a0` | `0x1c70a0` | 200 (ms) | Default Retransmission Timeout. |

## Analisis Celah (Vulnerabilities) untuk "Lag"

### 1. Flooding Update (Interval Starvation)
Pengurangan `IKCP_INTERVAL` dari 100ms menjadi 1ms memaksa protokol untuk memproses antrian dan mengirimkan ACK/Data jauh lebih sering. Dalam skenario pertandingan nyata, hal ini mengakibatkan:
- **CPU Spikes:** Pemrosesan paket yang terlalu sering mengonsumsi siklus CPU yang seharusnya digunakan untuk logika game.
- **Network Congestion:** Volume paket kecil (ACK) yang masif dapat memenuhi bandwidth unggahan, menyebabkan jitter dan packet loss.

### 2. Forced Compression Overhead (Zip Bomb Vector)
Terdapat logika kustom di sekitar `KCP_EnableZip` dan `KCP_IsZipEnabled` yang menggunakan LZ4/Zlib.
- **Celah:** Fungsi `KCP_IsZipEnabled` (offset `0xca7b0`) dapat dipatch untuk selalu mengembalikan `true`.
- **Dampak:** Memaksa setiap paket untuk melewati proses kompresi/dekompresi menambah latensi pemrosesan (overhead) pada setiap transmisi data, yang secara kumulatif terasa sebagai lag input.

## Metodologi PoC (lib-moba-test.so)

Untuk membuktikan konsep ini, `lib-moba-test.so` dibuat dengan memodifikasi nilai-nilai di atas secara langsung pada biner asli menggunakan skrip patching otomatis.

1. **Patch Interval:** Mengubah `0x1c70d0` menjadi `0x01 0x00 0x00 0x00`.
2. **Patch Window:** Mengubah `0x1c70c0` dan `0x1c70c4` menjadi `0x00 0x08 0x00 0x00` (2048).
3. **Patch Zip Logic:** Mengganti instruksi awal `KCP_IsZipEnabled` dengan `MOV W0, #1; RET` (Hex: `20 00 80 52 C0 03 5F D6`).

---
*Catatan: Modifikasi ini murni untuk tujuan analisis keamanan dan pemahaman risiko integritas file biner.*
