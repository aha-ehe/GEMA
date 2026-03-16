# Analisis Reverse Engineering KCP pada libmoba.so

## 1. Pendahuluan
Laporan ini berisi hasil _reverse engineering_ statis pada berkas pustaka `libmoba.so` dengan fokus pada penelusuran implementasi dan modifikasi protokol KCP (*KCP Custom*). Tujuan analisis ini adalah untuk memberikan dasar (*groundwork*) bagi rekayasa lebih lanjut, seperti modifikasi jaringan (network modding) dan eksekusi injeksi kode atau hooking melalui celah di `UnityPlayerActivity.smali`.

### Spesifikasi Target
- **File:** `libmoba.so`
- **Arsitektur:** ELF 64-bit LSB shared object, ARM aarch64 (ARM64)
- **Tooling:** Radare2 (`r2`), `nm`, `objdump`, `strings`.

## 2. Temuan Utama: KCP Ekstensi Kustom (Compression/Zip)
Satu modifikasi besar pada implementasi KCP standar di `libmoba.so` adalah adanya lapisan kompresi yang diatur melalui kontrol _zip_. Melalui analisis _string_ dan simbol, ditemukan beberapa fungsi wrapper khusus dengan prefiks `KCP_` yang tidak ada dalam implementasi standar `ikcp`.

### Fungsi Konfigurasi Kustom KCP
Pustaka ini memperluas `ikcp` dengan kontrol *zip* / *SevenZip*. Berikut adalah alamat memori (*offset*) dari fungsi-fungsi kontrol utama:

| Fungsi C++ / C | Offset (aarch64) | Deskripsi (Analisis Perilaku Statis) |
| --- | --- | --- |
| `KCP_EnableZip(int64_t arg1)` | `0x000ca7a0` | Menyimpan nilai argumen boolean (0 atau 1) ke alamat memori statis di segmen data (diindikasikan melalui variabel global `g_bEnableZip`). Menyalakan/mematikan kompresi paket. |
| `KCP_SetZipControlCode(int64_t arg1)`| `0x000ca7c0` | Menyimpan argumen berupa 32-bit integer (*Control Code*) ke alamat memori (variabel global `g_iZipControlCode`). Ini digunakan sebagai instruksi kode saat proses zip/unzip dijalankan. |
| `KCP_IsZipEnabled()` | `0x000ca7b0` | Membaca dan mengembalikan _flag_ boolean dari memori. Sering dipanggil sebelum melakukan proses _encoding/sending_. |
| `KCP_GetZipControlCode()` | `0x000ca7d0` | Mengembalikan nilai *Control Code* yang sedang berjalan. |

_Catatan Hooking:_ Jika ingin menonaktifkan enkripsi/kompresi sepenuhnya, melakukan *hooking* dan modifikasi _return value_ pada fungsi `KCP_IsZipEnabled` menjadi `0` merupakan vektor yang sangat mudah. Selain itu, mengubah argumen pada `KCP_EnableZip` bisa mencapai hasil yang serupa.

### String Terkait Ekstensi SevenZip
Ditemukan bahwa kompresi di-_handle_ oleh pustaka `lib7zip.so`. Beberapa log string menarik:
- `g_SevenZipSOLoaderObject`
- `_ExtractFile, lib7zip.so is NULL`
- `com/moba/sevenzip/SevenZipSOLoader`
Hal ini menunjukan _loader_ di sisi Java/Smali mencoba memanggil 7zip, dan kemungkinan besar fungsi `KCP_SendMsg` dan receive berinteraksi dengan kompresi ini.

## 3. Pemetaan Fungsi Core KCP (IKCP)
Selain wrapper kustom, kode asli KCP juga di-*compile* masuk ke dalam shared object ini. Berbeda dengan _stripped binaries_ biasa, simbol-simbol *exported* dari _core_ KCP secara mengejutkan dapat terlihat jelas (`T` pada _text segment_).

Berikut adalah offset untuk fungsi-fungsi kunci jika diperlukan pembuatan _hook_ untuk _sniffing_ (melihat payload mentah jaringan sebelum kompresi atau setelah dekompresi):

| Fungsi | Offset | Catatan Signature (Asumsi berdasarkan KCP Standar) |
| --- | --- | --- |
| `ikcp_create` | `0x000ce300` | `ikcpcb* ikcp_create(IUINT32 conv, void *user)` - Inisialisasi KCP |
| `ikcp_release` | `0x000ce4fc` | Mengalokasi kembali memori objek KCP |
| `ikcp_send` | `0x000ceb0c` | `int ikcp_send(ikcpcb *kcp, const char *buffer, int len)` - Fungsi ideal untuk dicegat (hook) agar dapat melihat *plaintext payload* yang akan dikirim sebelum diproses lebih lanjut. |
| `ikcp_recv` | `0x000ce7a0` | `int ikcp_recv(ikcpcb *kcp, char *buffer, int len)` - Fungsi ideal untuk *hook* pembacaan *plaintext payload* setelah diterima dari *server*. |
| `ikcp_update` | `0x000d0758` | Fungsi _clock update_ KCP yang wajib dipanggil di _loop_ utama (`KCP_ReceiveCycle` / `KCP_ReceiveCycleWithHandle`). |
| `ikcp_input` | `0x000cf0f0` | `int ikcp_input(ikcpcb *kcp, const char *data, long size)` - Input *raw packet* dari network (UDP). |
| `KCP_SendMsg` | `0x000ca540` | Wrapper level atas untuk pengiriman paket. Mengeksekusi pengecekan state Tpidr_el0 (Thread Pointer/TLS) sebelum memanggil layer jaringan di bawahnya. |
| `KCP_ReceiveCycle` | `0x000ca0d4` | Wrapper loop yang men-_dequeues_ dan memproses state receive message dari *queue/buffer* internal yang telah di-_handle_. |

## 4. Analisis Potensi Modifikasi (Patching / Hooking)

Berdasarkan *disassembly* struktur kontrol yang ada, ada dua layer arsitektur jaringan pada `libmoba.so`:
1. **Low Level (ikcp_*):** Merupakan algoritma *sliding window* dan ARQ KCP itu sendiri. Jika kita ingin mengubah cara kerja ARQ atau melakukan *sniffing* paket bersih (belum terenkripsi/terkompresi), maka melakukan _Inline Hook_ menggunakan *Framework* seperti Dobby pada `0x000ceb0c` (`ikcp_send`) dan `0x000ce7a0` (`ikcp_recv`) adalah yang paling disarankan.
2. **High Level Kustom (KCP_*):** Di sini terletak modifikasi *developer* terkait kompresi (Zip). Anda bisa mencegat inisialisasi pada _layer_ ini jika Anda ingin mengelabui server/klien untuk tidak menggunakan kompresi.

### Vektor lewat `UnityPlayerActivity.smali`
Karena Anda telah mencatat keberadaan `UnityPlayerActivity.smali`, kita dapat menyuntikkan (inject) file `.so` kustom kita pada metode inisialisasi utama (seperti `onCreate`). Langkahnya:
1. Kita buat _library_ C++ (`libhook.so`) yang meng-_include_ *framework hooking* (Dobby/AndHook).
2. Tulis kode yang melakukan pencarian *base address* `libmoba.so` di memori saat _runtime_.
3. Lakukan hook ke offset `0x000ceb0c` (untuk `ikcp_send`) dengan menggunakan `BaseAddress + 0x000ceb0c`.
4. Muat (_load_) `libhook.so` di dalam *file* Smali `UnityPlayerActivity` menggunakan pemanggilan JNI `System.loadLibrary("hook");`.

## 5. Kesimpulan
Modifikasi protokol KCP pada `libmoba.so` difokuskan pada pengintegrasian fitur dekompresi/kompresi data jaringan kustom melalui `lib7zip`. Karena nama _symbol_ fungsi asli `ikcp` sengaja dipertahankan (tidak sepenuhnya di-*strip*), _mapping_ memori untuk _hooking_ sangat mudah dan bisa dilakukan dengan _offset statis_ yang telah disajikan pada bagian 3.

---
*Laporan ini dihasilkan menggunakan static analysis. Untuk penelusuran lebih mendalam terhadap kontrol *flow* dari isi data / payload, disarankan melakukan dynamic analysis menggunakan perangkat (device) tersambung ke Frida.*
