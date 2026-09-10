# Aplikasi KlasterKu

Sistem Segmentasi Pelanggan & Manajemen Stok berbasis web untuk **PT Sinar Multi Kemindo**.

## Fitur Utama

- Upload dataset transaksi (CSV / Excel)
- Clustering pelanggan (K-Means) dengan label Tinggi / Sedang / Rendah
- Master Barang, Label, Kemasan (FIFO / LIFO)
- Barang / Label / Kemasan Masuk & Keluar (otomatis potong stok dari dataset)
- Search + Pagination
- Export Excel Master Data
- History Clustering & laporan

## Instalasi

```bash
# Clone repo
git clone https://github.com/aldiriy/Aplikasi_KlasterKu.git
cd Aplikasi_KlasterKu

# Virtual environment (opsional tapi disarankan)
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Migrasi database
python manage.py migrate

# Buat superuser
python manage.py createsuperuser

# Jalankan server
python manage.py runserver