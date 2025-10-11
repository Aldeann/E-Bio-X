# E-Bio-X

Platform E-Learning Biologi berbasis web yang dibangun menggunakan Nuxt 3.

## Fitur Utama

- Tutorial untuk pengguna baru [on progress]
- Sistem autentikasi multi-user (Admin, Guru, Siswa)
- Autentikasi dengan JWT atau google OAuth
- Fitur Guru:
  - Manajemen kelas
  - Manajemen materi pembelajaran
  - Manajemen kuis
  - Analisis performa siswa
- Fitur Siswa:
  - Akses materi pembelajaran
  - Partisipasi dalam kuis
  - Melihat hasil kuis
- Fitur Admin:
  - Manajemen pengguna (Guru, Siswa)
  - Manajemen kelas
  - Manajemen materi

## Tech Stack

- Nuxt 3
- Nuxt Toast
- Nuxt/icon
- Tailwind CSS
- SweetAlert2

## Requirments

- Node.js 
- NPM 

## Instalasi

1. Clone repository:
```bash
git clone https://github.com/Baghaztra/e-bio-x-frontend.git
cd e-bio-x
```

2. Install dependensi:
```bash
npm install
```

3. Salin file `.env.example` ke `.env` dan sesuaikan konfigurasi:
```bash
cp .env.example .env
```

4. Jalankan server development:
```bash
npm run dev
```

## Struktur Proyek

```
e-bio-x/
├── .nuxt/ 
├── components/ 
├── layouts/
├── pages/
│   ├── index.vue
│   ├── login.vue
│   └── teacher/        # Halaman khusus guru
│   └── student/        # Halaman khusus siswa
│   └── admin/          # Halaman khusus admin
├── public/
├── .env
├── nuxt.config.ts 
└── package.json
```

## Lisensi

[MIT License](LICENSE)
