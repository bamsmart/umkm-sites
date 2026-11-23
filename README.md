# umkm-sites

Generator website profil & katalog WhatsApp statis untuk ratusan klien UMKM, siap deploy otomatis ke **Cloudflare Pages**.

## Struktur Folder

```text
umkm-sites/
├── _template/
│   ├── index.html          # Master template halaman klien (SEO & OG WhatsApp)
│   ├── home.html           # Halaman root "/" agar domain utama tidak 404
│   ├── 404.html            # Custom 404 Cloudflare Pages
│   └── _headers            # Security & cache headers Cloudflare Pages
├── assets/
│   └── dapur-sds/          # Semua gambar lokal milik klien dapur-sds (logo, hero, menu, galeri)
├── data/
│   └── clients.json        # Database seluruh klien (tidak ikut ter-deploy)
├── scripts/
│   └── generate.py         # Generator halaman klien -> output ke folder public/
├── public/                 # Build output directory untuk Cloudflare Pages
│   ├── index.html
│   ├── 404.html
│   ├── _headers
│   └── dapur-sds/
│       ├── index.html      # Live di https://<domain>/dapur-sds/
│       └── assets/         # Disalin otomatis dari assets/dapur-sds/
└── .gitignore
```

## Alur Kerja 5 Menit (Tambah Klien Baru)

1. *(Jika ada foto dari klien)* Buat folder `assets/<slug-klien>/` lalu taruh file gambarnya (format `.webp` / `.jpg`, usahakan `< 300 KB`).
2. Tambahkan 1 objek klien baru ke `data/clients.json`.
3. Jalankan script generator:
   ```bash
   python3 scripts/generate.py
   ```
4. *(Opsional)* Preview lokal sebelum push:
   ```bash
   python3 -m http.server 8080 --directory public
   ```
   Buka `http://localhost:8080/<slug-klien>/`.
5. Commit dan push ke GitHub:
   ```bash
   git add . && git commit -m "add client: <slug-klien>" && git push
   ```
   Cloudflare Pages akan otomatis men-deploy dalam ~30–60 detik.

## Cara Mengelola & Mengganti Gambar Klien

Semua slot gambar (`logo`, `fotoHero`, `layanan[*].foto`, dan `galeri`) mendukung **2 cara**:

1. **File lokal di folder `assets/<slug>/` (paling rapi untuk foto dari WA klien):**
   Taruh gambar di `assets/dapur-sds/` (mis. `hero.jpg`, `logo.png`, `nasi-box.jpg`), lalu cukup tulis **nama filenya saja** di `data/clients.json`:
   ```json
   "logo": "logo.png",
   "fotoHero": "hero.jpg",
   "layanan": [
     {
       "nama": "Paket Nasi Box Komplit",
       "harga": "Rp25.000",
       "desc": "Nasi putih, lauk utama, sayur, sambal, lalapan.",
       "foto": "nasi-box.jpg",
       "populer": true
     }
   ],
   "galeri": [
     { "foto": "galeri-1.jpg", "caption": "Pesanan 50 box rapat" }
   ]
   ```
   Saat `python3 scripts/generate.py` dijalankan, script otomatis memvalidasi keberadaan file (anti broken image) dan menyalinnya ke `public/<slug>/assets/`.
2. **URL eksternal (CDN / Unsplash / Cloudflare R2):**
   Langsung tulis URL lengkap `https://...` pada field gambar yang diinginkan.

## Format `data/clients.json`

Setiap entri memiliki `slug` (huruf kecil, angka, dan `-`, tanpa spasi) dan objek `config`:

| Field | Wajib | Keterangan |
| --- | :---: | --- |
| `namaBisnis` | Ya | Nama usaha klien (tampil di navbar, hero, dan preview WA) |
| `kategori` | Ya | Kategori singkat usaha |
| `tagline` | Ya | Deskripsi singkat usaha (dipakai juga untuk meta description & OG) |
| `warnaUtama` | Ya | Kode hex warna tema utama (mis. `#c2410c`) |
| `warnaHover` | Ya | Kode hex warna hover tombol (mis. `#9a3412`) |
| `logo` | Opsional | Nama file di `assets/<slug>/` atau URL `https://` (tampil di navbar & favicon) |
| `fotoHero` | Ya | Nama file di `assets/<slug>/` atau URL `https://` (banner & thumbnail WA) |
| `whatsapp` | Ya | Nomor WA format internasional tanpa `+`/spasi (mis. `6281234567890`) |
| `pesanDefaultWA` | Ya | Pesan otomatis saat klik tombol WA utama |
| `keunggulan` | Opsional | Array `{ icon, judul, desc }` (ikon Font Awesome, mis. `fa-star`). Kosongkan `[]` untuk menyembunyikan section |
| `layanan` | Ya | Array `{ nama, harga, desc, foto?, populer }` |
| `galeri` | Opsional | Array `{ foto, caption? }` atau array nama file/URL. Kosongkan `[]` untuk menyembunyikan section |
| `testimoni` | Opsional | Array `{ nama, teks }`. Kosongkan `[]` untuk menyembunyikan section |
| `alamat` | Ya | Alamat lengkap usaha |
| `jamBuka` | Ya | Jam operasional |
| `linkGoogleMaps` | Ya | URL Google Maps lokasi usaha |
| `creditAgensi` | Opsional | Teks credit di footer. Kosongkan `""` untuk paket white-label |

## Update Template Massal

Untuk memperbaiki bug atau menambah fitur di seluruh halaman klien sekaligus:
1. Edit `_template/index.html`.
2. Jalankan `python3 scripts/generate.py`.
3. Commit dan push — seluruh halaman klien di `public/` langsung ter-update.

## Konfigurasi Cloudflare Pages

Saat menghubungkan repositori ini ke **Cloudflare Pages**:

- **Framework preset:** `None`
- **Build command:** `python3 scripts/generate.py`
- **Build output directory:** `public`
- *(Opsional, disarankan jika pakai custom domain & foto lokal untuk preview WA)* Tambahkan Environment Variable `SITE_URL=https://domainkamu.id` di Cloudflare Pages agar `og:image` memakai domain utama. *(Jika tidak diisi, Cloudflare otomatis menyediakan `CF_PAGES_URL`.)*

> **Keamanan:** Karena output diarahkan ke `public/`, file `data/clients.json`, `scripts/generate.py`, dan `_template/` tidak pernah terekspos ke publik.
