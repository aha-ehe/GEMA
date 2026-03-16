# Laporan Analisis KCP Kustom (`libmoba.so`)

## 1. Pendahuluan
Laporan ini berisi hasil _reverse engineering_ dan analisis biner terhadap _shared object_ `libmoba.so` yang digunakan pada sebuah game MOBA untuk menangani lalu lintas data UDP melalui protokol KCP. Analisis ini ditujukan untuk memetakan bagaimana game ini mengimplementasikan KCP, ekstensi apa saja yang ditambahkan, dan potensi celah keamanan yang mungkin ada.

## 2. Arsitektur dan Modifikasi KCP Kustom

Dari analisis tabel simbol (non-stripped exports) dan _disassembly_ menggunakan `aarch64-linux-gnu-objdump`, game ini mempertahankan fungsi asli KCP (dengan konvensi nama `ikcp_`), namun membungkusnya dalam beberapa API kustom yang diekspos (`KCP_*`).

### 2.1. Fungsi KCP Inti
Fungsi-fungsi standar KCP yang tetap digunakan meliputi:
* `ikcp_create`: Menginisialisasi instans KCP dan menggunakan memori alokator (`malloc` fallback).
* `ikcp_send` & `ikcp_recv`: Menangani pengiriman dan penerimaan buffer tingkat pengguna.
* `ikcp_input`: Fungsi utama yang memparsing data UDP mentah yang masuk ke lapisan KCP.
* `ikcp_setmtu`: Diatur untuk memastikan MTU memiliki batas minimal (dalam versi ini dicek `cmp w1, #0x32`, artinya MTU minimal 50 bytes).

### 2.2. Fungsi Pembungkus / Kustom Game (KCP Custom)
Game ini mengekspos fungsi-fungsi berikut yang berinteraksi langsung dengan KCP:
* **`KCP_EnableZip`** dan **`KCP_IsZipEnabled`**:
  Ini adalah ekstensi penting di lapisan KCP game ini. Analisis statis menunjukkan bahwa `KCP_EnableZip` menulis _flag_ (berupa nilai `1` byte, `strb`) ke offset tertentu dalam struktur konfigurasi global `runtime_error` _base_ (atau instance serupa).
* **`KCP_SendMsg`** dan **`KCP_ReceiveCycle`**:
  Berperan sebagai _loop_ perantara. Sebelum data diserahkan ke lapisan logika game, ia akan melalui `KCP_ReceiveCycle`.

### 2.3. Penggunaan Kompresi (Zip)
Protokol game sering kali di-compress untuk menghemat _bandwidth_ UDP. Data dari `KCP_SendMsg` tampaknya memeriksa status _flag_ Zip (dikembalikan oleh `KCP_IsZipEnabled`). Jika kompresi aktif, data akan dimampatkan sebelum di-enkapsulasi dalam paket KCP.

## 3. Identifikasi Potensi Celah Keamanan (Vulnerability Discovery)

### 3.1. Parsing Data yang Tidak Aman (KCP Input & Decompression)
Di dalam fungsi `ikcp_input`, data UDP mentah divalidasi dan dipecah berdasarkan struktur segmen KCP (cmd, frg, wnd, ts, sn, una, len).
* **Potensi _Integer/Buffer Overflow_ di Kompresi**: Karena implementasi ini mendukung kompresi (Zip), beban payload (`data`) yang diterima melalui `ikcp_recv` perlu di-dekompresi sebelum dipakai. Apabila logika dekompresi tidak memvalidasi rasio kompresi (misal ekspektasi ukuran asli `decompressed_size` vs aktual memori yang dialokasikan), maka _attacker_ bisa mengirim paket _zip bomb_ UDP yang menyebabkan _heap buffer overflow_ atau eksploitasi kehabisan memori (_OOM/Crash_).

### 3.2. Manipulasi Interval dan RTO
Fungsi `ikcp_nodelay` dan `ikcp_setmtu` digunakan untuk mempercepat interval ACK. Jika game server/client tidak melakukan pengecekan frekuensi pemanggilan di level UDP (misal limitasi paket per detik), seorang _attacker_ yang menginjeksi paket KCP secara konstan dapat melakukan eksploitasi **Denial of Service (DoS)** atau KCP _Flooding_ yang menyebabkan _CPU exhaustion_ saat server / client memproses `ikcp_input` dan pembacaan `acklist`.

### 3.3. Struktur Pointers pada Alokasi KCP
Pada `ikcp_release`, memori segmen dan _queue_ KCP dihapus. Jika manajemen koneksi multi-threading (terlihat adanya `UdpPipeManager`) tidak menggunakan penguncian (mutex/lock) yang aman di level pemanggilan `ikcp_release`, celah **_Use-After-Free_ (UAF)** bisa dimanfaatkan bila suatu _thread_ masih memegang _pointer_ paket `KCP_ReceiveCycle` yang sudah dilepaskan.

## 4. Kerentanan Kritis Disrupsi Server (Server DoS/Crash)
Analisis lebih dalam (Deep Dive) pada alur penerimaan pesan (`ikcp_parse_data`, `ikcp_recv`, dan `KCP_ReceiveCycle`) mengungkap skenario serangan yang dapat langsung menyebabkan server terganggu (_Crash_ atau mengalami DoS):

### 4.1 CPU Exhaustion melalui Fragmentasi KCP
Dalam `ikcp_parse_data` dan `ikcp_input`, data mentah UDP dipecah berdasarkan segmen (_frg_ - fragment id). Apabila penyerang (_attacker_) membuat paket manipulatif dengan memalsukan ID fragmen atau nilai ukuran payload (`len`) sedemikian rupa, *loop* penyatuan paket dapat berputar (iterasi) dalam jumlah tak masuk akal. Ini akan menyebabkan utas (_thread_) pekerja pada `UdpPipeManager` mengalami pemakaian CPU hingga 100% (**CPU Exhaustion**).

### 4.2 OOM Crash via _Exception Flooding_ (`KCP_ReceiveCycle`)
Disassembly dari `KCP_ReceiveCycle` (offset `0xca170` - `0xca1ac`) menunjukkan logika eksepsi (penggunaan `__cxa_allocate_exception` dan `__cxa_throw`) ketika terjadi kesalahan parsing atau _bad_type_id_ paket.
* **Vektor Eksploitasi**: Seorang penyerang bisa *membanjiri* koneksi dengan payload KCP *malformed* (rusak) sehingga memicu eksepsi berulang kali. Alokasi _exception_ terus menerus tanpa _rate limiting_ KCP akan menguras habis memori (_Memory Exhaustion_ / **OOM Crash**) pada server MOBA.

### 4.3 Heap Buffer Overflow Dinamis pada Dekompresi Zip
Sebagaimana dicatat di poin 3.1, `KCP_EnableZip` terintegrasi erat dengan layer aplikasi. Karena KCP membaca paket sebelum memvalidasi total rasio dekompresi di memori, payload yang disetel maksimal dengan algoritma kompresi tinggi (_Zip Bomb_) akan memaksa alokator (`malloc` fallback) menyalin ukuran tak terhingga ke _buffer_ layer game, mengakibatkan **Heap Buffer Overflow**. Jika server tidak di-compile dengan mitigasi yang kuat, hal ini memicu _Segmentation Fault_ (Crash).

## 5. Kesimpulan dan Rekomendasi
* **Cara Kerja**: KCP di `libmoba.so` adalah KCP standar yang digabungkan ke `UdpPipeManager` dengan modifikasi dukungan aktivasi/penonaktifan kompresi Zip di layer pengiriman/penerimaan.
* **Celah Kritis**: Paling berisiko terletak pada mekanisme _Decompression_ (Heap Overflow), loop fragmentasi _ikcp_parse_data_ (CPU DoS), dan Exception Flooding (OOM Crash).
* **Rekomendasi**:
  1. Tambahkan *rate limiter* pada port UDP penerima untuk menangkal injeksi paket sampah.
  2. Implementasikan batasan maksimum pada iterasi _re-assembly_ fragmen KCP.
  3. Validasi limit keras pada alokasi _buffer_ dekompresi dan tangani _error/exception_ tanpa memanggil `__cxa_allocate_exception` jika memungkinkan, atau ubah metode *error handling* KCP menjadi *silent drop*.

*(Laporan Analisis Mendalam Otomatis)*
