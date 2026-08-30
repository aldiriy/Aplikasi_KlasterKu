from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models import Sum


# ==========================================================
# CUSTOM USER
# ==========================================================
class CustomUser(AbstractUser):
    foto_profil = models.ImageField(
        upload_to="profil/",
        default="default.jpg",
        blank=True,
        null=True
    )
    no_hp = models.CharField(max_length=20, blank=True)
    alamat = models.TextField(blank=True)
    jabatan = models.CharField(max_length=100, blank=True)
    tanggal_lahir = models.DateField(blank=True, null=True)
    is_profile_complete = models.BooleanField(default=False)

    def __str__(self):
        return self.username


# ==========================================================
# CUSTOMER
# ==========================================================
class Customer(models.Model):
    nama_customer = models.CharField(max_length=255, verbose_name="Nama Customer")
    alamat = models.TextField(blank=True, null=True)
    no_telp = models.CharField(max_length=20, blank=True, null=True, verbose_name="No. Telepon")
    email = models.EmailField(blank=True, null=True)
    tanggal_bergabung = models.DateField(default=now, verbose_name="Tanggal Bergabung")

    # Statistik
    total_qty = models.FloatField(default=0)
    total_omzet = models.FloatField(default=0)
    area = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Master Customer"
        ordering = ["nama_customer"]

    def __str__(self):
        return self.nama_customer


# ==========================================================
# PERMINTAAN (Transaksi)
# ==========================================================
class Permintaan(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="permintaans"
    )
    tanggal = models.DateField()
    jenis_label = models.CharField(max_length=100)
    jenis_kemasan = models.CharField(max_length=100)
    jumlah = models.IntegerField(default=0)
    nilai = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    frekuensi = models.IntegerField(default=1)
    total_nilai = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Permintaan"
        verbose_name_plural = "Riwayat Permintaan"
        ordering = ["-tanggal"]

    def __str__(self):
        return f"{self.customer} - {self.jenis_label}"


# ==========================================================
# CLUSTERING HISTORY (Prioritas Tinggi)
# ==========================================================
class ClusteringHistory(models.Model):
    STATUS_CHOICES = [
        ("pending", "Menunggu"),
        ("processing", "Sedang Diproses"),
        ("completed", "Selesai"),
        ("failed", "Gagal"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="clustering_histories"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    total_data = models.PositiveIntegerField(default=0)
    n_clusters = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    algorithm = models.CharField(max_length=50, default="K-Means")

    silhouette_score = models.FloatField(null=True, blank=True)
    note = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "History Clustering"
        verbose_name_plural = "History Clustering"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Clustering #{self.id} - {self.created_at.strftime('%d %b %Y %H:%M')}"

    @property
    def duration(self):
        if self.finished_at and self.created_at:
            delta = self.finished_at - self.created_at
            return str(delta).split(".")[0]
        return "-"


class ClusterDetail(models.Model):
    history = models.ForeignKey(
        ClusteringHistory,
        on_delete=models.CASCADE,
        related_name="clusters"
    )
    cluster_label = models.IntegerField()  # 0, 1, 2, ...
    label_name = models.CharField(max_length=100, blank=True)  # High Value, At Risk, dll
    member_count = models.PositiveIntegerField(default=0)

    avg_monetary = models.FloatField(default=0)
    avg_frequency = models.FloatField(default=0)
    avg_recency = models.FloatField(default=0)  # dalam hari
    top_products = models.JSONField(default=list, blank=True)

    recommendation = models.TextField(blank=True)
    color = models.CharField(max_length=20, default="#0ea5e9")

    class Meta:
        verbose_name = "Detail Cluster"
        verbose_name_plural = "Detail Cluster"
        ordering = ["cluster_label"]
        unique_together = ["history", "cluster_label"]

    def __str__(self):
        return f"Cluster {self.cluster_label} - {self.label_name or 'Unlabeled'}"


class ClusterMember(models.Model):
    cluster = models.ForeignKey(
        ClusterDetail,
        on_delete=models.CASCADE,
        related_name="members"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="cluster_memberships",
        null=True,
        blank=True
    )
    customer_code = models.CharField(max_length=100, blank=True)
    customer_name = models.CharField(max_length=255)
    monetary = models.FloatField(default=0)
    frequency = models.FloatField(default=0)
    recency = models.FloatField(default=0)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Member Cluster"
        verbose_name_plural = "Member Cluster"
        ordering = ["-monetary"]

    def __str__(self):
        return f"{self.customer_name} → Cluster {self.cluster.cluster_label}"


# ==========================================================
# HASIL CLUSTERING (Legacy - tetap dipertahankan untuk kompatibilitas)
# ==========================================================
class HasilClustering(models.Model):
    """
    Menyimpan hasil clustering per customer.
    Disarankan diisi bersamaan saat ClusteringHistory dibuat.
    """
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="clusterings"
    )
    history = models.ForeignKey(
        ClusteringHistory,
        on_delete=models.CASCADE,
        related_name="hasil_customers",
        null=True,
        blank=True
    )
    cluster = models.IntegerField()
    tanggal_clustering = models.DateTimeField(auto_now_add=True)
    silhouette_score = models.FloatField(blank=True, null=True)

    class Meta:
        verbose_name = "Hasil Clustering"
        verbose_name_plural = "Hasil Clustering"
        ordering = ["-tanggal_clustering"]

    def __str__(self):
        return f"Cluster {self.cluster} - {self.customer}"


# ==========================================================
# USER PROFILE (Opsional - jika masih dipakai)
# ==========================================================
class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    foto = models.ImageField(
        upload_to="profile/",
        default="profile/default.png",
        blank=True
    )
    jabatan = models.CharField(max_length=100, default="Administrator")
    no_hp = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profile"

    def __str__(self):
        return self.user.username


# ==========================================================
# RIWAYAT UPLOAD
# ==========================================================
class UploadHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploads"
    )
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField(default=0)
    row_count = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Riwayat Upload"
        verbose_name_plural = "Riwayat Upload"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.file_name} - {self.user.username}"

    def get_file_size_display(self):
        size_kb = self.file_size / 1024
        if size_kb >= 1024:
            return f"{size_kb / 1024:.2f} MB"
        return f"{size_kb:.2f} KB"


# ==========================================================
# MASTER BARANG + STOK (FIFO / LIFO)
# ==========================================================
class KategoriBarang(models.Model):
    nama = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Kategori Barang"
        verbose_name_plural = "Kategori Barang"
        ordering = ["nama"]

    def __str__(self):
        return self.nama


class Barang(models.Model):
    METODE_CHOICES = [
        ("FIFO", "FIFO (First In First Out)"),
        ("LIFO", "LIFO (Last In First Out)"),
    ]

    kode_barang = models.CharField(max_length=50, unique=True)
    nama_barang = models.CharField(max_length=255)
    kategori = models.ForeignKey(
        KategoriBarang,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="barangs"
    )
    satuan = models.CharField(max_length=50, default="pcs")
    metode = models.CharField(max_length=10, choices=METODE_CHOICES, default="FIFO")
    stok_total = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Master Barang"
        verbose_name_plural = "Master Barang"
        ordering = ["nama_barang"]

    def __str__(self):
        return f"{self.kode_barang} - {self.nama_barang}"

    def hitung_stok(self):
        total = self.batches.aggregate(total=Sum("sisa"))["total"] or 0
        self.stok_total = total
        self.save(update_fields=["stok_total"])
        return total


class BatchBarang(models.Model):
    barang = models.ForeignKey(Barang, on_delete=models.CASCADE, related_name="batches")
    tanggal_masuk = models.DateField()
    qty_masuk = models.FloatField()
    qty_keluar = models.FloatField(default=0)
    sisa = models.FloatField()
    keterangan = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Batch Barang"
        verbose_name_plural = "Batch Barang"
        ordering = ["tanggal_masuk", "id"]

    def __str__(self):
        return f"{self.barang.kode_barang} | {self.tanggal_masuk} | Sisa: {self.sisa}"

    def save(self, *args, **kwargs):
        self.sisa = self.qty_masuk - self.qty_keluar
        super().save(*args, **kwargs)
        self.barang.hitung_stok()


class TransaksiBarang(models.Model):
    TIPE_CHOICES = [
        ("MASUK", "Barang Masuk"),
        ("KELUAR", "Barang Keluar"),
    ]

    barang = models.ForeignKey(Barang, on_delete=models.CASCADE, related_name="transaksis")
    tipe = models.CharField(max_length=10, choices=TIPE_CHOICES)
    qty = models.FloatField()
    tanggal = models.DateField()
    keterangan = models.TextField(blank=True, null=True)
    referensi = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Contoh: No Order / Nama Customer"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Transaksi Barang"
        verbose_name_plural = "Riwayat Transaksi Barang"
        ordering = ["-tanggal", "-created_at"]

    def __str__(self):
        return f"{self.tipe} | {self.barang.nama_barang} | {self.qty}"


# ==========================================================
# MASTER LABEL + STOK
# ==========================================================
class Label(models.Model):
    METODE_CHOICES = [
        ("FIFO", "FIFO (First In First Out)"),
        ("LIFO", "LIFO (Last In First Out)"),
    ]

    kode_label = models.CharField(max_length=50, unique=True)
    nama_label = models.CharField(max_length=255)
    gramasi = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Contoh: 50g, 100g, 1kg"
    )
    satuan = models.CharField(max_length=30, default="pcs")
    metode = models.CharField(max_length=10, choices=METODE_CHOICES, default="FIFO")
    stok_total = models.FloatField(default=0)
    keterangan = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Master Label"
        verbose_name_plural = "Master Label"
        ordering = ["nama_label"]

    def __str__(self):
        return f"{self.kode_label} - {self.nama_label}"

    def hitung_stok(self):
        total = self.batches.aggregate(total=Sum("sisa"))["total"] or 0
        self.stok_total = total
        self.save(update_fields=["stok_total"])
        return total


class BatchLabel(models.Model):
    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="batches")
    tanggal_masuk = models.DateField()
    qty_masuk = models.FloatField()
    qty_keluar = models.FloatField(default=0)
    sisa = models.FloatField()
    keterangan = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tanggal_masuk", "id"]

    def save(self, *args, **kwargs):
        self.sisa = self.qty_masuk - self.qty_keluar
        super().save(*args, **kwargs)
        self.label.hitung_stok()


class TransaksiLabel(models.Model):
    TIPE_CHOICES = [("MASUK", "Masuk"), ("KELUAR", "Keluar")]

    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="transaksis")
    tipe = models.CharField(max_length=10, choices=TIPE_CHOICES)
    qty = models.FloatField()
    tanggal = models.DateField()
    keterangan = models.TextField(blank=True, null=True)
    referensi = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-tanggal", "-created_at"]


# ==========================================================
# MASTER KEMASAN + STOK
# ==========================================================
class Kemasan(models.Model):
    METODE_CHOICES = [
        ("FIFO", "FIFO (First In First Out)"),
        ("LIFO", "LIFO (Last In First Out)"),
    ]

    kode_kemasan = models.CharField(max_length=50, unique=True)
    nama_kemasan = models.CharField(max_length=255)
    kapasitas = models.FloatField(
        null=True,
        blank=True,
        help_text="Contoh: 25 (untuk kemasan 25 kg)"
    )
    satuan_kapasitas = models.CharField(max_length=20, default="kg")
    satuan = models.CharField(max_length=30, default="pcs")
    metode = models.CharField(max_length=10, choices=METODE_CHOICES, default="FIFO")
    stok_total = models.FloatField(default=0)
    keterangan = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Master Kemasan"
        verbose_name_plural = "Master Kemasan"
        ordering = ["nama_kemasan"]

    def __str__(self):
        return f"{self.kode_kemasan} - {self.nama_kemasan}"

    def hitung_stok(self):
        total = self.batches.aggregate(total=Sum("sisa"))["total"] or 0
        self.stok_total = total
        self.save(update_fields=["stok_total"])
        return total


class BatchKemasan(models.Model):
    kemasan = models.ForeignKey(Kemasan, on_delete=models.CASCADE, related_name="batches")
    tanggal_masuk = models.DateField()
    qty_masuk = models.FloatField()
    qty_keluar = models.FloatField(default=0)
    sisa = models.FloatField()
    keterangan = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tanggal_masuk", "id"]

    def save(self, *args, **kwargs):
        self.sisa = self.qty_masuk - self.qty_keluar
        super().save(*args, **kwargs)
        self.kemasan.hitung_stok()


class TransaksiKemasan(models.Model):
    TIPE_CHOICES = [("MASUK", "Masuk"), ("KELUAR", "Keluar")]

    kemasan = models.ForeignKey(Kemasan, on_delete=models.CASCADE, related_name="transaksis")
    tipe = models.CharField(max_length=10, choices=TIPE_CHOICES)
    qty = models.FloatField()
    tanggal = models.DateField()
    keterangan = models.TextField(blank=True, null=True)
    referensi = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-tanggal", "-created_at"]


# ==========================================================
# JALUR ISTIMEWA
# ==========================================================
class JalurIstimewa(models.Model):
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="jalur_istimewa"
    )

    # Label
    pakai_label_ganda = models.BooleanField(
        default=False,
        help_text="Pakai label asli + label perusahaan"
    )
    label_asli = models.ForeignKey(
        Label, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    label_perusahaan = models.ForeignKey(
        Label, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    # Kemasan
    kemasan = models.ForeignKey(
        Kemasan, null=True, blank=True, on_delete=models.SET_NULL
    )
    ukuran_kemasan = models.FloatField(
        null=True, blank=True, help_text="Contoh: 25 (kg)"
    )

    # Special handling
    qc_extra = models.BooleanField(default=False)
    pakai_palet = models.BooleanField(default=False)
    diikat = models.BooleanField(default=False)
    relabel = models.BooleanField(default=False)

    catatan = models.TextField(blank=True, null=True, help_text="Catatan khusus untuk gudang")
    aktif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Jalur Istimewa"
        verbose_name_plural = "Jalur Istimewa"

    def __str__(self):
        return f"Jalur Istimewa - {self.customer.nama_customer}"


# ==========================================================
# STOK OPNAME
# ==========================================================
class StokOpname(models.Model):
    tanggal = models.DateField()
    file_name = models.CharField(max_length=255, blank=True)
    keterangan = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stok Opname"
        verbose_name_plural = "Stok Opname"
        ordering = ["-tanggal", "-created_at"]

    def __str__(self):
        return f"Opname {self.tanggal}"


class DetailStokOpname(models.Model):
    opname = models.ForeignKey(StokOpname, on_delete=models.CASCADE, related_name="details")
    barang = models.ForeignKey(Barang, on_delete=models.CASCADE)
    stok_sistem = models.FloatField()
    stok_fisik = models.FloatField()
    selisih = models.FloatField()  # fisik - sistem
    keterangan = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Detail Stok Opname"
        verbose_name_plural = "Detail Stok Opname"