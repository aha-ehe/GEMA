# KCP Payload Dump Analysis

Dokumen ini berisi hasil ekstraksi payload jaringan (KCP/UDP) dari sampel tangkapan jaringan (`hasil-awal-game.pcap`).

## 1. Statistik Tangkapan Jaringan
* **Total UDP Packets**: 4996
* **Total Unique Flows**: 6

Alur koneksi (flow) yang berhasil diidentifikasi mencakup percakapan (komunikasi) antara klien lokal (`10.215.173.1`) dengan beberapa server, termasuk trafik spesifik protokol KCP dan resolusi DNS.

## 2. Struktur Payload KCP yang Diekstrak

Pada aliran komunikasi ke Game Server (contoh: `103.157.33.7:5508`), paket UDP memiliki panjang 24 hingga 129 byte dengan pola _header_ yang berulang. Struktur _header_ (8 byte pertama) seperti `01 51 c2 a9 4e 79 8d 00` kemungkinan besar mewakili struktur kontrol KCP khusus:
- **Cmd/Frg/Wnd**: Indikasi kontrol window dan frg.
- **SN (Sequence Number) / UNA (Unacknowledged)**: Terlihat dalam inkrementasi hex di _flow_ tersebut.

### 2.1 Flow: Client -> KCP Server (`10.215.173.1:47565 -> 103.157.33.7:5508`)
*Trafik ini adalah koneksi klien MOBA ke game server.*

**[Payload 1] - Size: 45 bytes**
```text
Hex:   0151c2a94e798d00000066aab62d1f0000004001000015007000f5070132450a7000e3d4daed02021480060180
Ascii: .Q..Ny....f..-....@.....p....2E.p............
```

**[Payload 2] (ACK/Heartbeat) - Size: 24 bytes**
```text
Hex:   0152c2a94e798e000000ec02149c8d000000400100000000
Ascii: .R..Ny............@.....
```

**[Payload 3] - Size: 24 bytes**
```text
Hex:   0152c2a94e798f0000002e03149c8e000000400100000000
Ascii: .R..Ny............@.....
```

**[Payload 4] - Size: 24 bytes**
```text
Hex:   0152c2a94e79900000004f03149c8f000000400100000000
Ascii: .R..Ny....O.......@.....
```

---

### 2.2 Flow: KCP Server -> Client (`103.157.33.7:5508 -> 10.215.173.1:47565`)
*Respon dari game server ke client.*

**[Payload 1] - Size: 24 bytes**
```text
Hex:   0152c2a94e792000000066aab62d1f000000400100000000
Ascii: .R..Ny ...f..-....@.....
```

**[Payload 2] - Size: 50 bytes**
```text
Hex:   0151c2a94e79200000004f03149c8f000000400100001a007000f60701320303460f7000e3d4daed0201c586d0e0c9338080
Ascii: .Q..Ny ...O.......@.....p....2..F.p............3..
```

**[Payload 3] (Data Lengkap/Terkompresi) - Size: 129 bytes**
```text
Hex:   0152c2a94e79200000000fabb62d1f0000004002000000000151c2a94e79200000007003149c900000004001000051007000cd0801dae3a706030246437051027000e2c8e68106013843187000a79c01013c65030001006f000200d105000300db058004bb9383cd06807000e2c8e6810601ac014302708004bb9383cd06808080
Ascii: .R..Ny ......-....@......Q..Ny ...p.......@...Q.p..........FCpQ.p.......8C.p.....<e....o..................p.........C.p..........
```
*(Catatan: Karakteristik "01 52 / 01 51" kemungkinan membedakan command `CMD_PUSH` vs `CMD_ACK` pada KCP. Byte-byte sesudahnya membawa payload level aplikasi yang dibungkus Zip / encoding custom game).*

---

### 2.3 Flow: Client -> CDN / Secondary Server (`10.215.173.1:34313 -> 148.153.100.59:30190`)
*Koneksi TCP-like over UDP sekunder (biasanya untuk log atau heartbeat tambahan).*

**[Payload 1] - Size: 29 bytes**
```text
Hex:   0000001d70009d4e0101450c7000a8a1b1d497b89def0880800396bff6
Ascii: ....p..N..E.p................
```

**Respon Server - Size: 25 bytes**
```text
Hex:   0000001970009e4e0101460c7000a8a1b1d497b89def088080
Ascii: ....p..N..F.p............
```

---

### 2.4 Trafik DNS (Latar Belakang)
* `10.215.173.1` me-resolve `akmcdn.ml.youngjoygame.com` (yang terhubung ke layanan `akamaized.net`). Ini adalah domain CDN dari game tersebut, kemungkinan untuk mengunduh _resource_ / _update patch_.

## Kesimpulan Analisis Pcap
Dari payload di atas, terlihat bahwa `01 51` dan `01 52` adalah byte KCP Command yang menentukan tipe fragmen. Di dalam fragment _push_ (`01 51`), `libmoba.so` menambahkan magic byte KCP Kustom (`70 00 ...`) yang membungkus layer protobuf/kompresi zip game. Pola inkremental pada offset `0x08` (seperti `8d`, `8e`, `8f`...) adalah Sequence Number (`sn`) KCP kustom yang dikirimkan terus menerus sebagai sinkronisasi real-time.

*(Dokumentasi Extracted Payload - KCP Analysis Task)*