from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, update_session_auth_hash
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import date
from django.shortcuts import redirect
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .models import (
    Customer, UploadHistory, Barang, KategoriBarang, BatchBarang, TransaksiBarang,
    Label, BatchLabel, TransaksiLabel,
    Kemasan, BatchKemasan, TransaksiKemasan,
    JalurIstimewa, StokOpname, DetailStokOpname,
    # Clustering baru
    ClusteringHistory, ClusterDetail, ClusterMember,
)

from .forms import (
    LoginForm,
    RegisterForm,
    ChangePasswordForm,
    ProfileForm,
)

import os
import pandas as pd
import traceback

# ==========================================================
# DASHBOARD
# ==========================================================

@login_required
def dashboard(request):
    if not request.user.is_profile_complete:
        return redirect("profile")

    last_file = request.session.get("last_uploaded_file")
    result = request.session.get("clustering_result")

    context = {
        "total_customer": 0,
        "total_data": 0,
        "total_produk": 0,
        "total_qty": 0,
        "total_omzet": "0",
        "total_cluster": 0,
        "silhouette_score": "-",
        "last_upload": "Belum ada file",

        "top_sales": {},
        "top_customers": {},
        "top_products": {},

        "pie_labels": [],
        "pie_values": [],
        "cluster_counts": {},
        "centroids": [],
        "cluster_labels": [],
        "cluster_values": [],
    }

    # Ambil data clustering dari session
    if result:
        context["total_cluster"] = result.get("n_clusters", 0)
        context["silhouette_score"] = result.get("silhouette_score", "-")
        context["cluster_counts"] = result.get("cluster_counts", {})
        context["centroids"] = result.get("centroids", [])

        # Data untuk chart distribusi cluster
        if result.get("cluster_counts"):
            context["cluster_labels"] = [f"Cluster {int(k) + 1}" for k in result["cluster_counts"].keys()]
            context["cluster_values"] = list(result["cluster_counts"].values())

    # Ambil data real dari file upload terakhir
    if last_file and os.path.exists(last_file):
        try:
            if last_file.endswith(".xlsx"):
                df = pd.read_excel(last_file)
            else:
                df = pd.read_csv(last_file, encoding="latin1")

            df.columns = df.columns.str.strip()

            # Bersihkan data numerik
            if "Qty" in df.columns:
                df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)

            if "Total Harga" in df.columns:
                df["Total Harga"] = (
                    df["Total Harga"]
                    .astype(str)
                    .str.replace("Rp", "", regex=False)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", "", regex=False)
                    .str.strip()
                )
                df["Total Harga"] = pd.to_numeric(df["Total Harga"], errors="coerce").fillna(0)

            # KPI Utama
            context["total_data"] = len(df)
            context["last_upload"] = os.path.basename(last_file)

            if "Customer" in df.columns:
                context["total_customer"] = df["Customer"].nunique()

            if "Produk" in df.columns:
                context["total_produk"] = df["Produk"].nunique()

            if "Qty" in df.columns:
                context["total_qty"] = int(df["Qty"].sum())

            if "Total Harga" in df.columns:
                context["total_omzet"] = "{:,.0f}".format(df["Total Harga"].sum())

            # Top Sales
            if "Sales" in df.columns:
                context["top_sales"] = (
                    df.groupby("Sales").size().sort_values(ascending=False).head(5).to_dict()
                )

            # Top Customer
            if "Customer" in df.columns and "Total Harga" in df.columns:
                context["top_customers"] = (
                    df.groupby("Customer")["Total Harga"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                    .to_dict()
                )

            # Top Produk
            if "Produk" in df.columns:
                context["top_products"] = (
                    df.groupby("Produk").size().sort_values(ascending=False).head(5).to_dict()
                )

            # PIE CHART (Sales)
            if "Sales" in df.columns:
                pie = df.groupby("Sales").size().sort_values(ascending=False)
                context["pie_labels"] = [str(x) for x in pie.index.tolist()]
                context["pie_values"] = [int(x) for x in pie.tolist()]

        except Exception as e:
            print("Dashboard Error:", e)
            traceback.print_exc()

    return render(request, "dashboard.html", context)

from django.shortcuts import render
from django.utils import timezone
from .models import Barang  # Menggunakan model Barang sesuai models.py

def dashboard_view(request):
    # Mengambil barang dengan stok total paling sedikit
    barang_tersedikit = Barang.objects.order_by('stok_total').first()
    
    context = {
        'barang_tersedikit': barang_tersedikit,
    }
    return render(request, 'dashboard.html', context)
# ==========================================================
# UPLOAD DATASET
# ==========================================================

@login_required
def upload_data(request):
    if not request.user.is_profile_complete:
        return redirect("profile")

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")

        if uploaded_file is None:
            messages.error(request, "Silakan pilih file terlebih dahulu.")
            return render(request, "partials/upload_form.html")

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in [".csv", ".xlsx"]:
            messages.error(request, "File harus bertipe CSV atau XLSX.")
            return render(request, "partials/upload_form.html")

        try:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            storage = FileSystemStorage(location=upload_dir)
            filename = storage.save(uploaded_file.name, uploaded_file)
            file_path = storage.path(filename)

            request.session["last_uploaded_file"] = file_path
            request.session.pop("clustering_result", None)
            request.session.modified = True

            messages.success(request, f"Dataset '{filename}' berhasil diupload.")
            return redirect("dashboard")

        except Exception as e:
            messages.error(request, f"Gagal mengupload file: {str(e)}")
            return render(request, "partials/upload_form.html")

    return render(request, "partials/upload_form.html")


# ==========================================================
# RUN CLUSTERING
# ==========================================================

@login_required
def run_clustering(request):
    last_file = request.session.get("last_uploaded_file")

    if not last_file or not os.path.exists(last_file):
        return render(request, "partials/clustering_form.html", {
            "error": "Silakan upload dataset terlebih dahulu."
        })

    if request.method == "POST":
        history = None

        try:
            n_clusters = int(request.POST.get("n_clusters", 3))
            algorithm = request.POST.get("algorithm", "kmeans")

            # ============================================
            # 0. BUAT HISTORY
            # ============================================
            history = ClusteringHistory.objects.create(
                user=request.user,
                status="processing",
                n_clusters=n_clusters,
                algorithm=algorithm.upper() if algorithm else "K-Means",
                note=f"File: {os.path.basename(last_file)}"
            )

            # Baca file
            if last_file.endswith(".xlsx"):
                df = pd.read_excel(last_file)
            else:
                df = pd.read_csv(last_file, encoding="latin1")

            df.columns = df.columns.str.strip()

            # Cek kolom wajib
            required_cols = ["Customer", "Qty", "Total Harga"]
            for col in required_cols:
                if col not in df.columns:
                    history.status = "failed"
                    history.error_message = f"Kolom wajib tidak ditemukan: {col}"
                    history.finished_at = timezone.now()
                    history.save()
                    return render(request, "partials/clustering_form.html", {
                        "error": f"Dataset harus memiliki kolom: {', '.join(required_cols)}"
                    })

            # Bersihkan data
            df["Qty"] = pd.to_numeric(df["Qty"], errors="coerce").fillna(0)
            df["Total Harga"] = (
                df["Total Harga"]
                .astype(str)
                .str.replace("Rp", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            df["Total Harga"] = pd.to_numeric(df["Total Harga"], errors="coerce").fillna(0)

            # ============================================
            # 1. PENGURANGAN STOK BARANG (tetap dipertahankan)
            # ============================================
            stok_warnings = []

            if "Produk" in df.columns:
                produk_agg = df.groupby("Produk")["Qty"].sum().reset_index()

                for _, row in produk_agg.iterrows():
                    nama_produk = str(row["Produk"]).strip()
                    qty_keluar = float(row["Qty"])

                    if not nama_produk or qty_keluar <= 0:
                        continue

                    barang = Barang.objects.filter(nama_barang__iexact=nama_produk).first()

                    if barang is None:
                        stok_warnings.append(f"Produk '{nama_produk}' tidak ditemukan di Master Barang")
                        continue

                    berhasil, pesan = kurangi_stok_barang(
                        barang=barang,
                        qty_dibutuhkan=qty_keluar,
                        tanggal=date.today(),
                        keterangan="Order dari clustering",
                        referensi=f"File: {os.path.basename(last_file)}",
                        user=request.user
                    )

                    if not berhasil:
                        stok_warnings.append(pesan)

            # ============================================
            # 2. AGGREGASI SESUAI SKRIPSI
            # Frekuensi = jumlah transaksi
            # Total_Qty  = total pembelian (kg/ton)
            # Total_Omzet
            # ============================================
            customer_agg = df.groupby("Customer").agg({
                "Qty": "sum",
                "Total Harga": "sum",
                "Customer": "count"               # Frekuensi
            }).rename(columns={
                "Qty": "Total_Qty",
                "Total Harga": "Total_Omzet",
                "Customer": "Frekuensi"
            }).reset_index()

            customer_agg.columns = ["Customer", "Total_Qty", "Total_Omzet", "Frekuensi"]

            # Update / Create Master Customer
            for _, row in customer_agg.iterrows():
                nama_cust = str(row["Customer"]).strip()
                total_qty = float(row["Total_Qty"])
                total_omzet = float(row["Total_Omzet"])

                customer = Customer.objects.filter(nama_customer__iexact=nama_cust).first()
                if customer is None:
                    Customer.objects.create(
                        nama_customer=nama_cust,
                        total_qty=total_qty,
                        total_omzet=total_omzet
                    )
                else:
                    customer.total_qty += total_qty
                    customer.total_omzet += total_omzet
                    customer.save(update_fields=["total_qty", "total_omzet"])

            # ============================================
            # 3. CLUSTERING
            # ============================================
            if len(customer_agg) < n_clusters:
                history.status = "failed"
                history.error_message = f"Jumlah customer ({len(customer_agg)}) < jumlah cluster ({n_clusters})"
                history.finished_at = timezone.now()
                history.save()
                return render(request, "partials/clustering_form.html", {
                    "error": f"Jumlah customer ({len(customer_agg)}) lebih sedikit dari jumlah cluster ({n_clusters})."
                })

            # Fitur sesuai skripsi
            X = customer_agg[["Frekuensi", "Total_Qty", "Total_Omzet"]]

            from sklearn.preprocessing import StandardScaler
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score, davies_bouldin_score
            import numpy as np

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # --- Elbow Method ---
            inertias = []
            K_range = range(2, min(8, len(customer_agg)))
            for k in K_range:
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                km.fit(X_scaled)
                inertias.append(km.inertia_)

            # Saran k optimal sederhana
            diffs = np.diff(inertias)
            optimal_k_suggestion = list(K_range)[np.argmin(diffs) + 1] if len(diffs) > 0 else n_clusters

            # Jalankan K-Means
            model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            customer_agg["Cluster"] = model.fit_predict(X_scaled)

            # Evaluasi
            silhouette = round(silhouette_score(X_scaled, customer_agg["Cluster"]), 4)
            dbi = round(davies_bouldin_score(X_scaled, customer_agg["Cluster"]), 4)
            centers = scaler.inverse_transform(model.cluster_centers_)

            # ============================================
            # 4. LABEL: Tinggi / Sedang / Rendah
            # ============================================
            from .utils.clustering_helper import get_cluster_color

            cluster_stats = []
            for i in range(n_clusters):
                subset = customer_agg[customer_agg["Cluster"] == i]
                avg_freq = float(subset["Frekuensi"].mean()) if len(subset) else 0
                avg_qty = float(subset["Total_Qty"].mean()) if len(subset) else 0
                avg_omzet = float(subset["Total_Omzet"].mean()) if len(subset) else 0
                score = (avg_freq * 0.3) + (avg_qty * 0.4) + (avg_omzet * 0.3)
                cluster_stats.append({
                    "cluster_id": i,
                    "avg_freq": avg_freq,
                    "avg_qty": avg_qty,
                    "avg_omzet": avg_omzet,
                    "score": score,
                    "member_count": len(subset)
                })

            cluster_stats_sorted = sorted(cluster_stats, key=lambda x: x["score"], reverse=True)

            # Mapping label
            label_map = {}
            if n_clusters == 3:
                labels = ["Tinggi", "Sedang", "Rendah"]
            elif n_clusters == 2:
                labels = ["Tinggi", "Rendah"]
            else:
                labels = [f"Cluster {i+1}" for i in range(n_clusters)]
                labels[0] = "Tinggi"
                if n_clusters >= 3:
                    labels[-1] = "Rendah"
                    labels[n_clusters // 2] = "Sedang"

            for idx, stat in enumerate(cluster_stats_sorted):
                label_map[stat["cluster_id"]] = labels[idx] if idx < len(labels) else f"Cluster {stat['cluster_id']+1}"

            def get_recommendation_gudang(label):
                rekomendasi = {
                    "Tinggi": (
                        "Prioritas UTAMA. Siapkan stok bahan baku lebih banyak dan pastikan ketersediaan. "
                        "Customer ini sering membeli dan dalam jumlah besar. Jaga level stok agar tidak kosong."
                    ),
                    "Sedang": (
                        "Prioritas SEDANG. Pantau stok secara berkala. Siapkan stok sesuai pola rata-rata. "
                        "Bisa diberikan penawaran untuk meningkatkan frekuensi pembelian."
                    ),
                    "Rendah": (
                        "Prioritas RENDAH. Stok disiapkan minimal. Fokus pada efisiensi gudang. "
                        "Pertimbangkan strategi untuk meningkatkan frekuensi atau volume pembelian."
                    ),
                }
                return rekomendasi.get(label, "Analisis lebih lanjut diperlukan untuk menentukan prioritas stok.")

            # Simpan ke database
            for i in range(n_clusters):
                subset = customer_agg[customer_agg["Cluster"] == i]
                member_count = len(subset)
                avg_freq = float(subset["Frekuensi"].mean()) if member_count else 0
                avg_qty = float(subset["Total_Qty"].mean()) if member_count else 0
                avg_omzet = float(subset["Total_Omzet"].mean()) if member_count else 0

                label = label_map.get(i, f"Cluster {i+1}")

                cluster_obj = ClusterDetail.objects.create(
                    history=history,
                    cluster_label=i,
                    label_name=label,
                    member_count=member_count,
                    avg_monetary=avg_omzet,
                    avg_frequency=avg_freq,
                    avg_recency=0,
                    recommendation=get_recommendation_gudang(label),
                    color=get_cluster_color(label) if label in ["Tinggi", "Sedang", "Rendah"] else "#0ea5e9",
                )

                for _, row in subset.iterrows():
                    nama_cust = str(row["Customer"]).strip()
                    customer_obj = Customer.objects.filter(nama_customer__iexact=nama_cust).first()

                    ClusterMember.objects.create(
                        cluster=cluster_obj,
                        customer=customer_obj,
                        customer_code=str(customer_obj.id) if customer_obj else "",
                        customer_name=nama_cust,
                        monetary=float(row["Total_Omzet"]),
                        frequency=float(row["Frekuensi"]),
                        recency=0,
                        extra_data={"total_qty": float(row["Total_Qty"])}
                    )

            # Update history
            history.status = "completed"
            history.total_data = len(customer_agg)
            history.n_clusters = n_clusters
            history.silhouette_score = silhouette
            history.note = (
                f"File: {os.path.basename(last_file)} | "
                f"DBI: {dbi} | Saran k optimal (Elbow): {optimal_k_suggestion}"
            )
            history.finished_at = timezone.now()
            history.save()

            # ============================================
            # 5. SIMPAN KE SESSION
            # ============================================
            cluster_counts = {
                int(k): int(v)
                for k, v in customer_agg["Cluster"].value_counts().sort_index().to_dict().items()
            }

            cluster_members = {}
            for cluster_id in range(n_clusters):
                members = customer_agg[customer_agg["Cluster"] == cluster_id][
                    ["Customer", "Frekuensi", "Total_Qty", "Total_Omzet"]
                ].sort_values("Total_Qty", ascending=False)

                cluster_members[str(cluster_id)] = [
                    {
                        "customer": row["Customer"],
                        "frekuensi": int(row["Frekuensi"]),
                        "qty": round(row["Total_Qty"], 2),
                        "omzet": round(row["Total_Omzet"], 2)
                    }
                    for _, row in members.iterrows()
                ]

            output_dir = os.path.join(settings.MEDIA_ROOT, "hasil")
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, "hasil_clustering_customer.xlsx")
            customer_agg.to_excel(output_file, index=False)

            request.session["clustering_result"] = {
                "n_clusters": n_clusters,
                "algorithm": algorithm,
                "silhouette_score": silhouette,
                "dbi_score": dbi,
                "optimal_k_suggestion": optimal_k_suggestion,
                "file_path": last_file,
                "hasil_file": output_file,
                "cluster_counts": cluster_counts,
                "cluster_members": cluster_members,
                "total_customer_clustered": len(customer_agg),
                "centroids": [
                    {
                        "cluster": i + 1,
                        "frekuensi": round(c[0], 2),
                        "qty": round(c[1], 2),
                        "total_harga": round(c[2], 2)
                    }
                    for i, c in enumerate(centers)
                ],
                "stok_warnings": stok_warnings,
                "history_id": history.id,
                "label_map": {str(k): v for k, v in label_map.items()},
            }
            request.session.modified = True

            if stok_warnings:
                for w in stok_warnings[:8]:
                    messages.warning(request, w)
                if len(stok_warnings) > 8:
                    messages.warning(request, f"... dan {len(stok_warnings) - 8} peringatan lainnya.")

            messages.success(
                request,
                f"Clustering berhasil! {len(customer_agg)} customer dikelompokkan. "
                f"Silhouette: {silhouette} | DBI: {dbi} | Saran k optimal: {optimal_k_suggestion}"
            )

            return redirect("clustering_detail", pk=history.id)

        except Exception as e:
            print("=" * 60)
            print("ERROR CLUSTERING:")
            traceback.print_exc()
            print("=" * 60)

            if history:
                history.status = "failed"
                history.error_message = str(e)
                history.finished_at = timezone.now()
                history.save()

            return render(request, "partials/clustering_form.html", {
                "error": f"Gagal clustering: {str(e)}"
            })

    return render(request, "partials/clustering_form.html")


# ==========================================================
# HASIL CLUSTERING
# ==========================================================

@login_required
def clustering_result(request):
    result = request.session.get("clustering_result")
    if not result:
        return redirect("run_clustering")

    context = {
        "result": result,
        "cluster_counts": result.get("cluster_counts", {}),
        "centroids": result.get("centroids", []),
        "cluster_members": result.get("cluster_members", {}),
        "silhouette_score": result.get("silhouette_score", "-"),
        "n_clusters": result.get("n_clusters", 0),
        "algorithm": result.get("algorithm", "KMEANS").upper(),
        "total_customer_clustered": result.get("total_customer_clustered", 0),
        "total_data": sum(result.get("cluster_counts", {}).values()) if result.get("cluster_counts") else 0,
    }

    return render(request, "partials/clustering_result.html", context)

# ==========================================================
# DOWNLOAD REPORT
# ==========================================================

@login_required
def download_report(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from io import BytesIO
    from datetime import datetime

    result = request.session.get("clustering_result")
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER,
        textColor=colors.HexColor("#1e3a8a"), spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"), spaceAfter=6
    )
    heading_style = ParagraphStyle(
        'Heading', parent=styles['Heading2'], fontSize=11,
        textColor=colors.HexColor("#1e40af"), spaceBefore=14, spaceAfter=6
    )
    normal_style = ParagraphStyle(
        'NormalCustom', parent=styles['Normal'], fontSize=9, leading=13
    )
    small_style = ParagraphStyle(
        'Small', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.grey
    )

    story = []
    now = datetime.now()

    # ====================== HEADER ======================
    story.append(Paragraph("KLASTERKU", title_style))
    story.append(Paragraph("Customer Segmentation System", subtitle_style))
    story.append(Paragraph("PT Sinar Multi Kemindo", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=8))
    story.append(Paragraph(
        "<b>Laporan Hasil Clustering Customer</b>",
        ParagraphStyle('Center', parent=normal_style, alignment=TA_CENTER, fontSize=12)
    ))
    story.append(Paragraph(
        f"Dicetak: {now.strftime('%d %B %Y %H:%M')} WIB",
        ParagraphStyle('Center', parent=small_style, alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 12))

    if not result:
        story.append(Paragraph("Belum ada hasil clustering. Silakan jalankan clustering terlebih dahulu.", normal_style))
        doc.build(story)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Laporan_KlasterKu_{now.strftime("%Y%m%d_%H%M")}.pdf"'
        return response

    # Ambil data dengan aman
    n_clusters = result.get("n_clusters", 0)
    algorithm = str(result.get("algorithm", "kmeans")).upper()
    silhouette = result.get("silhouette_score", "-")
    total_customer = result.get("total_customer_clustered", 0)
    cluster_counts = result.get("cluster_counts", {})
    cluster_members = result.get("cluster_members", {})
    centroids = result.get("centroids", [])
    file_path = result.get("file_path", "-")

    # Hitung total dari cluster_counts (lebih aman)
    if not total_customer and cluster_counts:
        total_customer = sum(int(v) for v in cluster_counts.values())

    # ====================== 1. RINGKASAN ======================
    story.append(Paragraph("1. Ringkasan Hasil Clustering", heading_style))

    summary_data = [
        ["Jumlah Cluster", str(n_clusters)],
        ["Algoritma", algorithm],
        ["Silhouette Score", str(silhouette)],
        ["Total Perusahaan", f"{total_customer:,}".replace(",", ".")],
        ["Dataset", os.path.basename(file_path) if file_path != "-" else "-"],
    ]

    t = Table(summary_data, colWidths=[5.5*cm, 10.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#eff6ff")),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    # Penjelasan singkat Silhouette
    story.append(Paragraph(
        "<i>Catatan: Silhouette Score mengukur kualitas cluster. Nilai mendekati 1 = cluster semakin baik. "
        "Nilai 0.7 ke atas termasuk kategori baik.</i>",
        small_style
    ))

    # ====================== 2. DISTRIBUSI ======================
    story.append(Paragraph("2. Distribusi Perusahaan per Cluster", heading_style))

    dist_data = [["Cluster", "Jumlah Perusahaan", "Persentase"]]
    total = sum(int(v) for v in cluster_counts.values()) if cluster_counts else 0

    for k, v in sorted(cluster_counts.items(), key=lambda x: int(x[0])):
        persen = (int(v) / total * 100) if total else 0
        dist_data.append([
            f"Cluster {int(k)+1}",
            f"{int(v):,}".replace(",", "."),
            f"{persen:.1f}%"
        ])

    dist_data.append(["TOTAL", f"{total:,}".replace(",", "."), "100%"])

    t2 = Table(dist_data, colWidths=[4*cm, 6*cm, 6*cm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)

    # ====================== 3. DAFTAR PERUSAHAAN (TOP 15) ======================
    story.append(Paragraph("3. Daftar Perusahaan per Cluster (Top 15 berdasarkan Omzet)", heading_style))
    story.append(Paragraph(
        "<i>Hanya ditampilkan 15 perusahaan dengan total omzet tertinggi di setiap cluster agar laporan tetap ringkas dan mudah dibaca.</i>",
        small_style
    ))
    story.append(Spacer(1, 6))

    for cluster_id, members in sorted(cluster_members.items(), key=lambda x: int(x[0])):
        # Ambil top 15
        top_members = members[:15] if len(members) > 15 else members

        story.append(Paragraph(
            f"<b>Cluster {int(cluster_id)+1}</b> — Total {len(members)} perusahaan (ditampilkan {len(top_members)} teratas)",
            normal_style
        ))
        story.append(Spacer(1, 4))

        member_data = [["No", "Nama Perusahaan", "Total Qty", "Total Omzet (Rp)"]]
        for i, m in enumerate(top_members, 1):
            omzet = f"{m['omzet']:,.0f}".replace(",", ".")
            qty = f"{m['qty']:,.0f}".replace(",", ".")
            member_data.append([
                str(i),
                str(m["customer"])[:42],
                qty,
                omzet
            ])

        t3 = Table(member_data, colWidths=[1.2*cm, 8.5*cm, 2.8*cm, 3.5*cm])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t3)
        story.append(Spacer(1, 10))

    # ====================== 4. CENTROID ======================
    story.append(Paragraph("4. Centroid (Pusat Cluster)", heading_style))
    story.append(Paragraph(
        "<i>Centroid menunjukkan nilai rata-rata Qty dan Omzet di setiap cluster. "
        "Semakin tinggi nilainya, semakin besar karakteristik customer di cluster tersebut.</i>",
        small_style
    ))
    story.append(Spacer(1, 4))

    cent_data = [["Cluster", "Rata-rata Qty", "Rata-rata Omzet (Rp)"]]
    for c in centroids:
        cent_data.append([
            f"Cluster {c['cluster']}",
            f"{c['qty']:,.2f}".replace(",", "."),
            f"{c['total_harga']:,.0f}".replace(",", ".")
        ])

    t4 = Table(cent_data, colWidths=[4*cm, 5*cm, 7*cm])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#dc2626")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t4)

    # ====================== 5. INTERPRETASI SINGKAT ======================
    story.append(Paragraph("5. Interpretasi Singkat (untuk Skripsi)", heading_style))

    interpretasi = """
    <b>Cluster 1</b> : Customer dengan qty dan omzet menengah.<br/>
    <b>Cluster 2</b> : Customer besar / high-value (qty dan omzet sangat tinggi). Jumlahnya sedikit tetapi sangat penting.<br/>
    <b>Cluster 3</b> : Customer kecil (mayoritas). Qty dan omzet rendah.<br/><br/>
    Cluster 2 merupakan segmen yang paling strategis untuk diberikan pelayanan khusus (Jalur Istimewa).
    """
    story.append(Paragraph(interpretasi, normal_style))

    # ====================== FOOTER ======================
    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#94a3b8"), spaceAfter=6))
    story.append(Paragraph(
        "Laporan digenerate otomatis oleh sistem <b>KlasterKu</b> • PT Sinar Multi Kemindo • © 2026",
        ParagraphStyle('Footer', parent=small_style, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)

    filename = f"Laporan_KlasterKu_{now.strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# ==========================================================
# LOGIN, REGISTER, CHANGE PASSWORD, LOGOUT, PROFILE
# ==========================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LoginForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)

        if not user.is_profile_complete:
            return redirect("profile")
        return redirect("dashboard")

    return render(request, "login.html", {"form": form})


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = RegisterForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("profile")

    return render(request, "register.html", {"form": form})


from django.contrib.auth import logout
from django.shortcuts import redirect

@login_required
def logout_view(request):
    logout(request)
    request.session.flush()
    messages.success(request, "Anda berhasil keluar dari sistem.")
    return redirect("login")


@login_required
def change_password(request):
    form = ChangePasswordForm(request.user, request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Password berhasil diubah.")
        return redirect("dashboard")

    return render(request, "change_password.html", {"form": form})

# ==========================================================
# MASTER CUSTOMER
# ==========================================================

@login_required
def master_customer(request):
    customers = Customer.objects.all().order_by("nama_customer")
    return render(request, "partials/master_customer.html", {
        "customers": customers
    })


@login_required
def tambah_customer(request):
    if request.method == "POST":
        nama = request.POST.get("nama_customer")
        alamat = request.POST.get("alamat")
        no_telp = request.POST.get("no_telp")
        email = request.POST.get("email")
        area = request.POST.get("area")

        if nama:
            Customer.objects.create(
                nama_customer=nama,
                alamat=alamat,
                no_telp=no_telp,
                email=email,
                area=area
            )
            messages.success(request, "Customer berhasil ditambahkan.")
            return redirect("master_customer")

    return render(request, "partials/tambah_customer.html")


@login_required
def edit_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        customer.nama_customer = request.POST.get("nama_customer")
        customer.alamat = request.POST.get("alamat")
        customer.no_telp = request.POST.get("no_telp")
        customer.email = request.POST.get("email")
        customer.area = request.POST.get("area")
        customer.save()
        messages.success(request, "Customer berhasil diupdate.")
        return redirect("master_customer")

    return render(request, "partials/edit_customer.html", {
        "customer": customer
    })


@login_required
def hapus_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.delete()
    messages.success(request, "Customer berhasil dihapus.")
    return redirect("master_customer")


# ==========================================================
# UPLOAD + DAFTAR FILE
# ==========================================================

@login_required
def upload_data(request):
    if not request.user.is_profile_complete:
        return redirect("profile")

    # Ambil daftar file yang sudah diupload
    upload_list = UploadHistory.objects.filter(user=request.user).order_by("-uploaded_at")

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")

        if uploaded_file is None:
            messages.error(request, "Silakan pilih file terlebih dahulu.")
            return render(request, "partials/upload_form.html", {"upload_list": upload_list})

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in [".csv", ".xlsx"]:
            messages.error(request, "File harus bertipe CSV atau XLSX.")
            return render(request, "partials/upload_form.html", {"upload_list": upload_list})

        try:
            # Simpan file fisik
            upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            storage = FileSystemStorage(location=upload_dir)
            filename = storage.save(uploaded_file.name, uploaded_file)
            file_path = storage.path(filename)
            file_size = os.path.getsize(file_path)

            # Baca file untuk hitung jumlah baris
            if ext == ".xlsx":
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path, encoding="latin1")

            row_count = len(df)

            # Simpan riwayat upload
            UploadHistory.objects.create(
                user=request.user,
                file_name=filename,
                file_path=file_path,
                file_size=file_size,
                row_count=row_count
            )

            # Simpan path ke session (untuk clustering)
            request.session["last_uploaded_file"] = file_path
            request.session.modified = True

            messages.success(request, f"File '{filename}' berhasil diupload ({row_count} baris).")
            return redirect("upload_data")

        except Exception as e:
            messages.error(request, f"Gagal mengupload: {str(e)}")
            traceback.print_exc()

    return render(request, "partials/upload_form.html", {
        "upload_list": upload_list
    })


@login_required
def hapus_upload(request, pk):
    upload = get_object_or_404(UploadHistory, pk=pk, user=request.user)

    # Hapus file fisik
    if os.path.exists(upload.file_path):
        try:
            os.remove(upload.file_path)
        except:
            pass

    # Hapus dari session kalau ini file terakhir
    if request.session.get("last_uploaded_file") == upload.file_path:
        request.session.pop("last_uploaded_file", None)
        request.session.pop("clustering_result", None)

    upload.delete()
    messages.success(request, "File berhasil dihapus.")
    return redirect("upload_data")

@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            user = form.save(commit=False)

            if all([
                user.first_name,
                user.email,
                getattr(user, "no_hp", None),
                getattr(user, "alamat", None),
                getattr(user, "jabatan", None),
            ]):
                user.is_profile_complete = True

            user.save()

            messages.success(request, "Profil berhasil diperbarui.")
            return redirect("dashboard")

    else:
        form = ProfileForm(instance=request.user)

    return render(request, "profile.html", {"form": form})

# ==========================================================
# MASTER BARANG
# ==========================================================

@login_required
def master_barang(request):
    barangs = Barang.objects.select_related("kategori").all().order_by("nama_barang")
    return render(request, "partials/master_barang.html", {
        "barangs": barangs
    })


@login_required
def tambah_barang(request):
    kategoris = KategoriBarang.objects.all()

    if request.method == "POST":
        kode = request.POST.get("kode_barang", "").strip()
        nama = request.POST.get("nama_barang", "").strip()
        kategori_id = request.POST.get("kategori")
        satuan = request.POST.get("satuan", "pcs").strip()
        metode = request.POST.get("metode", "FIFO")
        qty_masuk = float(request.POST.get("qty_masuk") or 0)
        tanggal_masuk = request.POST.get("tanggal_masuk") or date.today().isoformat()

        if not kode or not nama:
            messages.error(request, "Kode dan Nama Barang wajib diisi.")
            return redirect("tambah_barang")

        if Barang.objects.filter(kode_barang=kode).exists():
            messages.error(request, f"Kode barang '{kode}' sudah ada.")
            return redirect("tambah_barang")

        kategori = None
        if kategori_id:
            kategori = KategoriBarang.objects.filter(pk=kategori_id).first()

        barang = Barang.objects.create(
            kode_barang=kode,
            nama_barang=nama,
            kategori=kategori,
            satuan=satuan,
            metode=metode,
            stok_total=0
        )

        # Buat batch pertama (barang masuk)
        if qty_masuk > 0:
            BatchBarang.objects.create(
                barang=barang,
                tanggal_masuk=tanggal_masuk,
                qty_masuk=qty_masuk,
                qty_keluar=0,
                sisa=qty_masuk,
                keterangan="Stok awal"
            )
            TransaksiBarang.objects.create(
                barang=barang,
                tipe="MASUK",
                qty=qty_masuk,
                tanggal=tanggal_masuk,
                keterangan="Stok awal",
                created_by=request.user
            )

        messages.success(request, f"Barang '{nama}' berhasil ditambahkan.")
        return redirect("master_barang")

    return render(request, "partials/tambah_barang.html", {
        "kategoris": kategoris
    })


@login_required
def edit_barang(request, pk):
    barang = get_object_or_404(Barang, pk=pk)
    kategoris = KategoriBarang.objects.all()

    if request.method == "POST":
        barang.kode_barang = request.POST.get("kode_barang", "").strip()
        barang.nama_barang = request.POST.get("nama_barang", "").strip()
        kategori_id = request.POST.get("kategori")
        barang.satuan = request.POST.get("satuan", "pcs").strip()
        barang.metode = request.POST.get("metode", "FIFO")

        if kategori_id:
            barang.kategori = KategoriBarang.objects.filter(pk=kategori_id).first()
        else:
            barang.kategori = None

        barang.save()
        messages.success(request, "Barang berhasil diupdate.")
        return redirect("master_barang")

    return render(request, "partials/edit_barang.html", {
        "barang": barang,
        "kategoris": kategoris
    })


@login_required
def hapus_barang(request, pk):
    barang = get_object_or_404(Barang, pk=pk)
    nama = barang.nama_barang
    barang.delete()
    messages.success(request, f"Barang '{nama}' berhasil dihapus.")
    return redirect("master_barang")


@login_required
def barang_masuk(request, pk):
    """Tambah stok (buat batch baru)"""
    barang = get_object_or_404(Barang, pk=pk)

    if request.method == "POST":
        qty = float(request.POST.get("qty") or 0)
        tanggal = request.POST.get("tanggal") or date.today().isoformat()
        keterangan = request.POST.get("keterangan", "")

        if qty <= 0:
            messages.error(request, "Qty harus lebih dari 0.")
            return redirect("barang_masuk", pk=pk)

        BatchBarang.objects.create(
            barang=barang,
            tanggal_masuk=tanggal,
            qty_masuk=qty,
            qty_keluar=0,
            sisa=qty,
            keterangan=keterangan or "Barang masuk"
        )
        TransaksiBarang.objects.create(
            barang=barang,
            tipe="MASUK",
            qty=qty,
            tanggal=tanggal,
            keterangan=keterangan or "Barang masuk",
            created_by=request.user
        )

        messages.success(request, f"Berhasil menambah stok {qty} {barang.satuan}.")
        return redirect("master_barang")

    return render(request, "partials/barang_masuk.html", {
        "barang": barang
    })


@login_required
def detail_barang(request, pk):
    """Lihat batch + riwayat transaksi"""
    barang = get_object_or_404(Barang, pk=pk)
    batches = barang.batches.all()
    transaksis = barang.transaksis.all()[:50]

    return render(request, "partials/detail_barang.html", {
        "barang": barang,
        "batches": batches,
        "transaksis": transaksis
    })


# ==========================================================
# FUNGSI FIFO / LIFO (dipakai saat ada order)
# ==========================================================

def kurangi_stok_barang(barang, qty_dibutuhkan, tanggal=None, keterangan="", referensi="", user=None):
    """
    Mengurangi stok barang menggunakan metode FIFO atau LIFO.
    Return: (berhasil: bool, pesan: str)
    """
    if tanggal is None:
        tanggal = date.today()

    if barang.stok_total < qty_dibutuhkan:
        return False, f"Stok {barang.nama_barang} tidak cukup. Sisa: {barang.stok_total}"

    # Ambil batch sesuai metode
    if barang.metode == "FIFO":
        batches = barang.batches.filter(sisa__gt=0).order_by("tanggal_masuk", "id")
    else:  # LIFO
        batches = barang.batches.filter(sisa__gt=0).order_by("-tanggal_masuk", "-id")

    sisa_kebutuhan = qty_dibutuhkan

    for batch in batches:
        if sisa_kebutuhan <= 0:
            break

        ambil = min(batch.sisa, sisa_kebutuhan)
        batch.qty_keluar += ambil
        batch.sisa -= ambil
        batch.save()

        sisa_kebutuhan -= ambil

    # Catat transaksi keluar
    TransaksiBarang.objects.create(
        barang=barang,
        tipe="KELUAR",
        qty=qty_dibutuhkan,
        tanggal=tanggal,
        keterangan=keterangan,
        referensi=referensi,
        created_by=user
    )

    return True, f"Berhasil mengurangi {qty_dibutuhkan} {barang.satuan}"


def kurangi_stok_label(label, qty_dibutuhkan, tanggal=None, keterangan="", referensi="", user=None):
    if tanggal is None:
        tanggal = date.today()

    if label.stok_total < qty_dibutuhkan:
        return False, f"Stok Label '{label.nama_label}' tidak cukup. Sisa: {label.stok_total}"

    if label.metode == "FIFO":
        batches = label.batches.filter(sisa__gt=0).order_by("tanggal_masuk", "id")
    else:
        batches = label.batches.filter(sisa__gt=0).order_by("-tanggal_masuk", "-id")

    sisa_kebutuhan = qty_dibutuhkan
    for batch in batches:
        if sisa_kebutuhan <= 0:
            break
        ambil = min(batch.sisa, sisa_kebutuhan)
        batch.qty_keluar += ambil
        batch.sisa -= ambil
        batch.save()
        sisa_kebutuhan -= ambil

    TransaksiLabel.objects.create(
        label=label,
        tipe="KELUAR",
        qty=qty_dibutuhkan,
        tanggal=tanggal,
        keterangan=keterangan,
        referensi=referensi,
        created_by=user
    )
    return True, f"Berhasil mengurangi {qty_dibutuhkan} {label.satuan} label"


def kurangi_stok_kemasan(kemasan, qty_dibutuhkan, tanggal=None, keterangan="", referensi="", user=None):
    if tanggal is None:
        tanggal = date.today()

    if kemasan.stok_total < qty_dibutuhkan:
        return False, f"Stok Kemasan '{kemasan.nama_kemasan}' tidak cukup. Sisa: {kemasan.stok_total}"

    if kemasan.metode == "FIFO":
        batches = kemasan.batches.filter(sisa__gt=0).order_by("tanggal_masuk", "id")
    else:
        batches = kemasan.batches.filter(sisa__gt=0).order_by("-tanggal_masuk", "-id")

    sisa_kebutuhan = qty_dibutuhkan
    for batch in batches:
        if sisa_kebutuhan <= 0:
            break
        ambil = min(batch.sisa, sisa_kebutuhan)
        batch.qty_keluar += ambil
        batch.sisa -= ambil
        batch.save()
        sisa_kebutuhan -= ambil

    TransaksiKemasan.objects.create(
        kemasan=kemasan,
        tipe="KELUAR",
        qty=qty_dibutuhkan,
        tanggal=tanggal,
        keterangan=keterangan,
        referensi=referensi,
        created_by=user
    )
    return True, f"Berhasil mengurangi {qty_dibutuhkan} {kemasan.satuan} kemasan"


# ==========================================================
# MASTER LABEL
# ==========================================================

@login_required
def master_label(request):
    labels = Label.objects.all().order_by("nama_label")
    return render(request, "partials/master_label.html", {"labels": labels})


@login_required
def tambah_label(request):
    if request.method == "POST":
        kode = request.POST.get("kode_label", "").strip()
        nama = request.POST.get("nama_label", "").strip()
        gramasi = request.POST.get("gramasi", "").strip()
        satuan = request.POST.get("satuan", "pcs").strip()
        metode = request.POST.get("metode", "FIFO")
        qty_masuk = float(request.POST.get("qty_masuk") or 0)
        tanggal_masuk = request.POST.get("tanggal_masuk") or date.today().isoformat()

        if not kode or not nama:
            messages.error(request, "Kode dan Nama Label wajib diisi.")
            return redirect("tambah_label")

        if Label.objects.filter(kode_label=kode).exists():
            messages.error(request, f"Kode label '{kode}' sudah ada.")
            return redirect("tambah_label")

        label = Label.objects.create(
            kode_label=kode,
            nama_label=nama,
            gramasi=gramasi,
            satuan=satuan,
            metode=metode,
            stok_total=0
        )

        if qty_masuk > 0:
            BatchLabel.objects.create(
                label=label,
                tanggal_masuk=tanggal_masuk,
                qty_masuk=qty_masuk,
                qty_keluar=0,
                sisa=qty_masuk,
                keterangan="Stok awal"
            )
            TransaksiLabel.objects.create(
                label=label, tipe="MASUK", qty=qty_masuk,
                tanggal=tanggal_masuk, keterangan="Stok awal", created_by=request.user
            )

        messages.success(request, f"Label '{nama}' berhasil ditambahkan.")
        return redirect("master_label")

    return render(request, "partials/tambah_label.html")


@login_required
def edit_label(request, pk):
    label = get_object_or_404(Label, pk=pk)
    if request.method == "POST":
        label.kode_label = request.POST.get("kode_label", "").strip()
        label.nama_label = request.POST.get("nama_label", "").strip()
        label.gramasi = request.POST.get("gramasi", "").strip()
        label.satuan = request.POST.get("satuan", "pcs").strip()
        label.metode = request.POST.get("metode", "FIFO")
        label.save()
        messages.success(request, "Label berhasil diupdate.")
        return redirect("master_label")
    return render(request, "partials/edit_label.html", {"label": label})


@login_required
def hapus_label(request, pk):
    label = get_object_or_404(Label, pk=pk)
    nama = label.nama_label
    label.delete()
    messages.success(request, f"Label '{nama}' berhasil dihapus.")
    return redirect("master_label")


@login_required
def label_masuk(request, pk):
    label = get_object_or_404(Label, pk=pk)
    if request.method == "POST":
        qty = float(request.POST.get("qty") or 0)
        tanggal = request.POST.get("tanggal") or date.today().isoformat()
        keterangan = request.POST.get("keterangan", "")

        if qty <= 0:
            messages.error(request, "Qty harus lebih dari 0.")
            return redirect("label_masuk", pk=pk)

        BatchLabel.objects.create(
            label=label, tanggal_masuk=tanggal,
            qty_masuk=qty, qty_keluar=0, sisa=qty,
            keterangan=keterangan or "Label masuk"
        )
        TransaksiLabel.objects.create(
            label=label, tipe="MASUK", qty=qty,
            tanggal=tanggal, keterangan=keterangan or "Label masuk",
            created_by=request.user
        )
        messages.success(request, f"Berhasil menambah stok {qty} {label.satuan}.")
        return redirect("master_label")

    return render(request, "partials/label_masuk.html", {"label": label})


@login_required
def detail_label(request, pk):
    label = get_object_or_404(Label, pk=pk)
    batches = label.batches.all()
    transaksis = label.transaksis.all()[:50]
    return render(request, "partials/detail_label.html", {
        "label": label, "batches": batches, "transaksis": transaksis
    })


@login_required
def upload_label(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Silakan pilih file Excel terlebih dahulu.")
            return redirect("upload_label")

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in [".xlsx", ".xls", ".csv"]:
            messages.error(request, "File harus berformat Excel (.xlsx) atau CSV.")
            return redirect("upload_label")

        try:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "upload_label")
            os.makedirs(upload_dir, exist_ok=True)
            storage = FileSystemStorage(location=upload_dir)
            filename = storage.save(uploaded_file.name, uploaded_file)
            file_path = storage.path(filename)

            if ext == ".csv":
                df = pd.read_csv(file_path, encoding="latin1")
            else:
                df = pd.read_excel(file_path)

            df.columns = df.columns.str.strip()

            # Normalisasi nama kolom (supaya fleksibel)
            col_map = {}
            for col in df.columns:
                col_lower = col.lower().replace("_", " ")
                if "kode" in col_lower:
                    col_map[col] = "kode_label"
                elif "nama" in col_lower:
                    col_map[col] = "nama_label"
                elif "qty" in col_lower or "jumlah" in col_lower or "stok" in col_lower:
                    col_map[col] = "qty"
                elif "satuan" in col_lower:
                    col_map[col] = "satuan"
                elif "tanggal" in col_lower:
                    col_map[col] = "tanggal_masuk"
                elif "metode" in col_lower:
                    col_map[col] = "metode"
                elif "gramasi" in col_lower:
                    col_map[col] = "gramasi"

            df = df.rename(columns=col_map)

            # Cek kolom wajib
            required = ["kode_label", "nama_label", "qty"]
            for col in required:
                if col not in df.columns:
                    messages.error(request, f"Kolom wajib tidak ditemukan: {col}")
                    return redirect("upload_label")

            berhasil = 0
            gagal = 0
            pesan_gagal = []

            for _, row in df.iterrows():
                try:
                    kode = str(row["kode_label"]).strip()
                    nama = str(row["nama_label"]).strip()
                    qty = float(row["qty"]) if pd.notna(row["qty"]) else 0

                    if not kode or not nama or qty <= 0:
                        continue

                    satuan = str(row.get("satuan", "Pcs")).strip() if pd.notna(row.get("satuan")) else "Pcs"
                    metode = str(row.get("metode", "FIFO")).strip().upper() if pd.notna(row.get("metode")) else "FIFO"
                    if metode not in ["FIFO", "LIFO"]:
                        metode = "FIFO"

                    gramasi = str(row.get("gramasi", "")).strip() if pd.notna(row.get("gramasi")) else ""

                    tanggal = row.get("tanggal_masuk")
                    if pd.isna(tanggal):
                        tanggal = date.today()
                    else:
                        tanggal = pd.to_datetime(tanggal).date()

                    # Buat atau update Label
                    label, created = Label.objects.get_or_create(
                        kode_label=kode,
                        defaults={
                            "nama_label": nama,
                            "gramasi": gramasi,
                            "satuan": satuan,
                            "metode": metode,
                            "stok_total": 0
                        }
                    )

                    if not created:
                        # Update data jika sudah ada
                        label.nama_label = nama
                        label.gramasi = gramasi
                        label.satuan = satuan
                        label.metode = metode
                        label.save()

                    # Tambah batch stok
                    BatchLabel.objects.create(
                        label=label,
                        tanggal_masuk=tanggal,
                        qty_masuk=qty,
                        qty_keluar=0,
                        sisa=qty,
                        keterangan=f"Upload Excel - {filename}"
                    )

                    TransaksiLabel.objects.create(
                        label=label,
                        tipe="MASUK",
                        qty=qty,
                        tanggal=tanggal,
                        keterangan=f"Upload Excel - {filename}",
                        created_by=request.user
                    )

                    berhasil += 1

                except Exception as e:
                    gagal += 1
                    pesan_gagal.append(f"{kode} - {str(e)}")

            if berhasil > 0:
                messages.success(request, f"Berhasil mengimpor {berhasil} label dari file.")
            if gagal > 0:
                messages.warning(request, f"{gagal} baris gagal diproses.")
                for p in pesan_gagal[:5]:
                    messages.warning(request, p)

            return redirect("master_label")

        except Exception as e:
            messages.error(request, f"Gagal membaca file: {str(e)}")
            traceback.print_exc()
            return redirect("upload_label")

    return render(request, "partials/upload_label.html")
# ==========================================================
# MASTER KEMASAN
# ==========================================================

@login_required
def master_kemasan(request):
    kemasans = Kemasan.objects.all().order_by("nama_kemasan")
    
    print("===== DEBUG MASTER KEMASAN =====")
    print("Jumlah data:", kemasans.count())
    for k in kemasans:
        print(k.id, k.kode_kemasan, k.nama_kemasan, k.stok_total)
    print("================================")
    
    return render(request, "partials/master_kemasan.html", {"kemasans": kemasans})


@login_required
def tambah_kemasan(request):
    if request.method == "POST":
        kode = request.POST.get("kode_kemasan", "").strip()
        nama = request.POST.get("nama_kemasan", "").strip()
        kapasitas = request.POST.get("kapasitas") or None
        satuan_kapasitas = request.POST.get("satuan_kapasitas", "kg").strip()
        satuan = request.POST.get("satuan", "pcs").strip()
        metode = request.POST.get("metode", "FIFO")
        qty_masuk = float(request.POST.get("qty_masuk") or 0)
        tanggal_masuk = request.POST.get("tanggal_masuk") or date.today().isoformat()

        if not kode or not nama:
            messages.error(request, "Kode dan Nama Kemasan wajib diisi.")
            return redirect("tambah_kemasan")

        if Kemasan.objects.filter(kode_kemasan=kode).exists():
            messages.error(request, f"Kode kemasan '{kode}' sudah ada.")
            return redirect("tambah_kemasan")

        kemasan = Kemasan.objects.create(
            kode_kemasan=kode,
            nama_kemasan=nama,
            kapasitas=float(kapasitas) if kapasitas else None,
            satuan_kapasitas=satuan_kapasitas,
            satuan=satuan,
            metode=metode,
            stok_total=0
        )

        if qty_masuk > 0:
            BatchKemasan.objects.create(
                kemasan=kemasan, tanggal_masuk=tanggal_masuk,
                qty_masuk=qty_masuk, qty_keluar=0, sisa=qty_masuk,
                keterangan="Stok awal"
            )
            TransaksiKemasan.objects.create(
                kemasan=kemasan, tipe="MASUK", qty=qty_masuk,
                tanggal=tanggal_masuk, keterangan="Stok awal", created_by=request.user
            )

            # Update stok total
            kemasan.stok_total = qty_masuk
            kemasan.save(update_fields=["stok_total"])

        messages.success(request, f"Kemasan '{nama}' berhasil ditambahkan.")
        return redirect("master_kemasan")

    return render(request, "partials/tambah_kemasan.html")

@login_required
def edit_kemasan(request, pk):
    kemasan = get_object_or_404(Kemasan, pk=pk)
    if request.method == "POST":
        kemasan.kode_kemasan = request.POST.get("kode_kemasan", "").strip()
        kemasan.nama_kemasan = request.POST.get("nama_kemasan", "").strip()
        kapasitas = request.POST.get("kapasitas") or None
        kemasan.kapasitas = float(kapasitas) if kapasitas else None
        kemasan.satuan_kapasitas = request.POST.get("satuan_kapasitas", "kg").strip()
        kemasan.satuan = request.POST.get("satuan", "pcs").strip()
        kemasan.metode = request.POST.get("metode", "FIFO")
        kemasan.save()
        messages.success(request, "Kemasan berhasil diupdate.")
        return redirect("master_kemasan")
    return render(request, "partials/edit_kemasan.html", {"kemasan": kemasan})


@login_required
def hapus_kemasan(request, pk):
    kemasan = get_object_or_404(Kemasan, pk=pk)
    nama = kemasan.nama_kemasan
    kemasan.delete()
    messages.success(request, f"Kemasan '{nama}' berhasil dihapus.")
    return redirect("master_kemasan")


@login_required
def kemasan_masuk(request, pk):
    kemasan = get_object_or_404(Kemasan, pk=pk)
    if request.method == "POST":
        qty = float(request.POST.get("qty") or 0)
        tanggal = request.POST.get("tanggal") or date.today().isoformat()
        keterangan = request.POST.get("keterangan", "")

        if qty <= 0:
            messages.error(request, "Qty harus lebih dari 0.")
            return redirect("kemasan_masuk", pk=pk)

        BatchKemasan.objects.create(
            kemasan=kemasan,
            tanggal_masuk=tanggal,
            qty_masuk=qty,
            qty_keluar=0,
            sisa=qty,
            keterangan=keterangan or "Kemasan masuk"
        )
        TransaksiKemasan.objects.create(
            kemasan=kemasan,
            tipe="MASUK",
            qty=qty,
            tanggal=tanggal,
            keterangan=keterangan or "Kemasan masuk",
            created_by=request.user
        )

        # Update stok total
        kemasan.stok_total = (kemasan.stok_total or 0) + qty
        kemasan.save(update_fields=["stok_total"])

        messages.success(request, f"Berhasil menambah stok {qty} {kemasan.satuan}.")
        return redirect("master_kemasan")

    return render(request, "partials/kemasan_masuk.html", {"kemasan": kemasan})

@login_required
def detail_kemasan(request, pk):
    kemasan = get_object_or_404(Kemasan, pk=pk)
    batches = kemasan.batches.all()
    transaksis = kemasan.transaksis.all()[:50]
    return render(request, "partials/detail_kemasan.html", {
        "kemasan": kemasan, "batches": batches, "transaksis": transaksis
    })



@login_required
def upload_kemasan(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Silakan pilih file Excel terlebih dahulu.")
            return redirect("upload_kemasan")

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in [".xlsx", ".xls", ".csv"]:
            messages.error(request, "File harus berformat Excel (.xlsx) atau CSV.")
            return redirect("upload_kemasan")

        try:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "upload_kemasan")
            os.makedirs(upload_dir, exist_ok=True)
            storage = FileSystemStorage(location=upload_dir)
            filename = storage.save(uploaded_file.name, uploaded_file)
            file_path = storage.path(filename)

            if ext == ".csv":
                df = pd.read_csv(file_path, encoding="latin1")
            else:
                df = pd.read_excel(file_path)

            df.columns = df.columns.str.strip()

            # Normalisasi nama kolom
            col_map = {}
            for col in df.columns:
                col_lower = col.lower().replace("_", " ")
                if "kode" in col_lower:
                    col_map[col] = "kode_kemasan"
                elif "nama" in col_lower:
                    col_map[col] = "nama_kemasan"
                elif "qty" in col_lower or "jumlah" in col_lower or "stok" in col_lower:
                    col_map[col] = "qty"
                elif "satuan" in col_lower and "kapasitas" not in col_lower:
                    col_map[col] = "satuan"
                elif "kapasitas" in col_lower:
                    col_map[col] = "kapasitas"
                elif "tanggal" in col_lower:
                    col_map[col] = "tanggal_masuk"
                elif "metode" in col_lower:
                    col_map[col] = "metode"

            df = df.rename(columns=col_map)

            required = ["kode_kemasan", "nama_kemasan", "qty"]
            for col in required:
                if col not in df.columns:
                    messages.error(request, f"Kolom wajib tidak ditemukan: {col}")
                    return redirect("upload_kemasan")

            berhasil = 0
            gagal = 0
            pesan_gagal = []

            for _, row in df.iterrows():
                try:
                    kode = str(row["kode_kemasan"]).strip()
                    nama = str(row["nama_kemasan"]).strip()
                    qty = float(row["qty"]) if pd.notna(row["qty"]) else 0

                    if not kode or not nama or qty <= 0:
                        continue

                    satuan = str(row.get("satuan", "Pcs")).strip() if pd.notna(row.get("satuan")) else "Pcs"
                    metode = str(row.get("metode", "FIFO")).strip().upper() if pd.notna(row.get("metode")) else "FIFO"
                    if metode not in ["FIFO", "LIFO"]:
                        metode = "FIFO"

                    kapasitas = None
                    if "kapasitas" in row and pd.notna(row["kapasitas"]):
                        try:
                            kapasitas = float(row["kapasitas"])
                        except:
                            kapasitas = None

                    tanggal = row.get("tanggal_masuk")
                    if pd.isna(tanggal):
                        tanggal = date.today()
                    else:
                        tanggal = pd.to_datetime(tanggal).date()

                    kemasan, created = Kemasan.objects.get_or_create(
                        kode_kemasan=kode,
                        defaults={
                            "nama_kemasan": nama,
                            "kapasitas": kapasitas,
                            "satuan_kapasitas": "kg",
                            "satuan": satuan,
                            "metode": metode,
                            "stok_total": 0
                        }
                    )

                    if not created:
                        kemasan.nama_kemasan = nama
                        kemasan.satuan = satuan
                        kemasan.metode = metode
                        if kapasitas is not None:
                            kemasan.kapasitas = kapasitas
                        kemasan.save()

                    kemasan, created = Kemasan.objects.get_or_create(
                    kode_kemasan=kode,
                    defaults={
                    "nama_kemasan": nama,
                    "kapasitas": kapasitas,
                    "satuan_kapasitas": "kg",
                    "satuan": satuan,
                    "metode": metode,
                    "stok_total": 0
                        }
                    )
                    print(f">>> SAVE: {kode} | created={created} | id={kemasan.id}")

                    TransaksiKemasan.objects.create(
                        kemasan=kemasan,
                        tipe="MASUK",
                        qty=qty,
                        tanggal=tanggal,
                        keterangan=f"Upload Excel - {filename}",
                        created_by=request.user
                    )

                    # Update stok total
                    kemasan.stok_total = (kemasan.stok_total or 0) + qty
                    kemasan.save(update_fields=["stok_total"])

                    berhasil += 1

                except Exception as e:
                    gagal += 1
                    pesan_gagal.append(f"{kode} - {str(e)}")

            if berhasil > 0:
                messages.success(request, f"Berhasil mengimpor {berhasil} kemasan dari file.")
            if gagal > 0:
                messages.warning(request, f"{gagal} baris gagal diproses.")
                for p in pesan_gagal[:5]:
                    messages.warning(request, p)

            return redirect("master_kemasan")

        except Exception as e:
            messages.error(request, f"Gagal membaca file: {str(e)}")
            traceback.print_exc()
            return redirect("upload_kemasan")

    return render(request, "partials/upload_kemasan.html")

@login_required
def upload_stok_barang(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Silakan pilih file Excel terlebih dahulu.")
            return redirect("upload_stok_barang")

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in [".xlsx", ".xls", ".csv"]:
            messages.error(request, "File harus berformat Excel (.xlsx) atau CSV.")
            return redirect("upload_stok_barang")

        try:
            upload_dir = os.path.join(settings.MEDIA_ROOT, "stok_opname")
            os.makedirs(upload_dir, exist_ok=True)
            storage = FileSystemStorage(location=upload_dir)
            filename = storage.save(uploaded_file.name, uploaded_file)
            file_path = storage.path(filename)

            if ext == ".csv":
                df = pd.read_csv(file_path, encoding="latin1")
            else:
                df = pd.read_excel(file_path)

            df.columns = df.columns.str.strip()

            # Normalisasi nama kolom
            col_map = {}
            for col in df.columns:
                col_lower = col.lower()
                if "kode" in col_lower:
                    col_map[col] = "kode_barang"
                elif "nama" in col_lower:
                    col_map[col] = "nama_barang"
                elif "qty" in col_lower or "jumlah" in col_lower or "stok" in col_lower:
                    col_map[col] = "qty"
                elif "satuan" in col_lower:
                    col_map[col] = "satuan"
                elif "tanggal" in col_lower:
                    col_map[col] = "tanggal_masuk"
                elif "metode" in col_lower:
                    col_map[col] = "metode"
                elif "kategori" in col_lower:
                    col_map[col] = "kategori"

            df = df.rename(columns=col_map)

            required = ["kode_barang", "nama_barang", "qty"]
            for col in required:
                if col not in df.columns:
                    messages.error(request, f"Kolom wajib tidak ditemukan: {col}")
                    return redirect("upload_stok_barang")

            berhasil = 0
            gagal = 0
            pesan_gagal = []

            for _, row in df.iterrows():
                try:
                    kode = str(row["kode_barang"]).strip()
                    nama = str(row["nama_barang"]).strip()
                    qty = float(row["qty"]) if pd.notna(row["qty"]) else 0

                    if not kode or not nama or qty <= 0:
                        continue

                    satuan = str(row.get("satuan", "Kg")).strip() if pd.notna(row.get("satuan")) else "Kg"
                    metode = str(row.get("metode", "FIFO")).strip().upper() if pd.notna(row.get("metode")) else "FIFO"
                    if metode not in ["FIFO", "LIFO"]:
                        metode = "FIFO"

                    tanggal = row.get("tanggal_masuk")
                    if pd.isna(tanggal):
                        tanggal = date.today()
                    else:
                        tanggal = pd.to_datetime(tanggal).date()

                    barang, created = Barang.objects.get_or_create(
                        kode_barang=kode,
                        defaults={
                            "nama_barang": nama,
                            "satuan": satuan,
                            "metode": metode,
                            "stok_total": 0
                        }
                    )

                    if not created:
                        barang.nama_barang = nama
                        barang.satuan = satuan
                        barang.metode = metode
                        barang.save()

                    BatchBarang.objects.create(
                        barang=barang,
                        tanggal_masuk=tanggal,
                        qty_masuk=qty,
                        qty_keluar=0,
                        sisa=qty,
                        keterangan=f"Upload Stok Opname - {filename}"
                    )

                    TransaksiBarang.objects.create(
                        barang=barang,
                        tipe="MASUK",
                        qty=qty,
                        tanggal=tanggal,
                        keterangan=f"Upload Stok Opname - {filename}",
                        created_by=request.user
                    )

                    berhasil += 1

                except Exception as e:
                    gagal += 1
                    pesan_gagal.append(f"{kode} - {str(e)}")

            if berhasil > 0:
                messages.success(request, f"Berhasil mengimpor {berhasil} barang dari file.")
            if gagal > 0:
                messages.warning(request, f"{gagal} baris gagal diproses.")
                for p in pesan_gagal[:5]:
                    messages.warning(request, p)

            return redirect("master_barang")

        except Exception as e:
            messages.error(request, f"Gagal membaca file: {str(e)}")
            traceback.print_exc()
            return redirect("upload_stok_barang")

    return render(request, "partials/upload_stok_barang.html")

@login_required
def clustering_history(request):
    histories = ClusteringHistory.objects.filter(user=request.user)
    
    # Filter status
    status = request.GET.get('status')
    if status:
        histories = histories.filter(status=status)
    
    # Search
    q = request.GET.get('q')
    if q:
        histories = histories.filter(
            Q(note__icontains=q) | Q(id__icontains=q)
        )
    
    context = {
        'histories': histories,
        'status_filter': status,
        'q': q or '',
    }
    return render(request, 'clustering/history.html', context)


# ===================== DETAIL HISTORY =====================
@login_required
def clustering_detail(request, pk):
    history = get_object_or_404(ClusteringHistory, pk=pk, user=request.user)
    clusters = history.clusters.all()

    # Ambil DBI dan saran Elbow dari note (kalau ada)
    dbi_score = None
    optimal_k = None

    if history.note:
        # Contoh note: "File: xxx.xlsx | DBI: 0.5123 | Saran k optimal (Elbow): 3"
        parts = history.note.split("|")
        for part in parts:
            part = part.strip()
            if part.startswith("DBI:"):
                try:
                    dbi_score = float(part.replace("DBI:", "").strip())
                except:
                    pass
            if "Saran k optimal" in part:
                try:
                    optimal_k = int(part.split(":")[-1].strip())
                except:
                    pass

    context = {
        'history': history,
        'clusters': clusters,
        'dbi_score': dbi_score,
        'optimal_k': optimal_k,
    }
    return render(request, 'clustering/detail.html', context)


# ===================== MEMBER CLUSTER =====================
@login_required
def cluster_members(request, pk, cluster_id):
    history = get_object_or_404(ClusteringHistory, pk=pk, user=request.user)
    cluster = get_object_or_404(ClusterDetail, history=history, cluster_label=cluster_id)
    
    members = cluster.members.all()
    
    # Search
    q = request.GET.get('q')
    if q:
        members = members.filter(
            Q(customer_name__icontains=q) | Q(customer_code__icontains=q)
        )
    
    context = {
        'history': history,
        'cluster': cluster,
        'members': members,
        'q': q or '',
    }
    return render(request, 'clustering/members.html', context)


# ===================== STATUS (AJAX) =====================
@login_required
def clustering_status(request, pk):
    history = get_object_or_404(ClusteringHistory, pk=pk, user=request.user)
    return JsonResponse({
        'status': history.status,
        'status_display': history.get_status_display(),
        'total_data': history.total_data,
        'n_clusters': history.n_clusters,
        'error_message': history.error_message,
    })


# ===================== EXPORT EXCEL =====================
@login_required
def export_clustering_excel(request, pk):
    history = get_object_or_404(ClusteringHistory, pk=pk, user=request.user)
    
    wb = Workbook()
    
    # Sheet 1: Ringkasan
    ws1 = wb.active
    ws1.title = "Ringkasan"
    
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="123458")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    ws1['A1'] = "Laporan Hasil Clustering"
    ws1['A1'].font = Font(bold=True, size=14)
    ws1['A2'] = f"ID: #{history.id}"
    ws1['A3'] = f"Tanggal: {history.created_at.strftime('%d %B %Y %H:%M')}"
    ws1['A4'] = f"Algoritma: {history.algorithm}"
    ws1['A5'] = f"Jumlah Data: {history.total_data}"
    ws1['A6'] = f"Jumlah Cluster: {history.n_clusters}"
    if history.silhouette_score:
        ws1['A7'] = f"Silhouette Score: {history.silhouette_score:.4f}"
    
    # Sheet 2: Detail Cluster
    ws2 = wb.create_sheet("Detail Cluster")
    headers = ['Cluster', 'Label', 'Jumlah Member', 'Avg Monetary', 'Avg Frequency', 'Avg Recency', 'Rekomendasi']
    for col, header in enumerate(headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border
    
    for row, cluster in enumerate(history.clusters.all(), 2):
        ws2.cell(row=row, column=1, value=cluster.cluster_label).border = thin_border
        ws2.cell(row=row, column=2, value=cluster.label_name).border = thin_border
        ws2.cell(row=row, column=3, value=cluster.member_count).border = thin_border
        ws2.cell(row=row, column=4, value=cluster.avg_monetary).border = thin_border
        ws2.cell(row=row, column=5, value=cluster.avg_frequency).border = thin_border
        ws2.cell(row=row, column=6, value=cluster.avg_recency).border = thin_border
        ws2.cell(row=row, column=7, value=cluster.recommendation).border = thin_border
    
    # Sheet 3: Member
    ws3 = wb.create_sheet("Member Cluster")
    headers3 = ['Cluster', 'Kode Customer', 'Nama Customer', 'Monetary', 'Frequency', 'Recency']
    for col, header in enumerate(headers3, 1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    row = 2
    for cluster in history.clusters.all():
        for member in cluster.members.all():
            ws3.cell(row=row, column=1, value=cluster.cluster_label).border = thin_border
            ws3.cell(row=row, column=2, value=member.customer_code).border = thin_border
            ws3.cell(row=row, column=3, value=member.customer_name).border = thin_border
            ws3.cell(row=row, column=4, value=member.monetary).border = thin_border
            ws3.cell(row=row, column=5, value=member.frequency).border = thin_border
            ws3.cell(row=row, column=6, value=member.recency).border = thin_border
            row += 1
    
    # Auto width
    for ws in [ws2, ws3]:
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws.column_dimensions[column_letter].width = min(max_length + 2, 40)
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"Clustering_{history.id}_{history.created_at.strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

    # ==========================================================
# PREFERENSI & TEMA
# ==========================================================
@login_required
def preferensi(request):
    return render(request, "preferensi.html")


# ==========================================================
# PENGADUAN
# ==========================================================
@login_required
def pengaduan(request):
    if request.method == "POST":
        # Sementara hanya simpan pesan sukses
        messages.success(request, "Pengaduan berhasil dikirim. Terima kasih!")
        return redirect("pengaduan")
    return render(request, "pengaduan.html")



@login_required
def preprocessing_bersih(request):
    last_file = request.session.get("last_uploaded_file")
    context = {
        "has_file": False,
        "filename": None,
        "total_rows": 0,
        "total_columns": 0,
        "null_count": 0,
        "duplicate_count": 0,
        "preview": None,
        "columns": [],
    }

    if last_file and os.path.exists(last_file):
        try:
            if last_file.endswith(".xlsx"):
                df = pd.read_excel(last_file)
            else:
                df = pd.read_csv(last_file, encoding="latin1")

            df.columns = df.columns.str.strip()

            context["has_file"] = True
            context["filename"] = os.path.basename(last_file)
            context["total_rows"] = len(df)
            context["total_columns"] = len(df.columns)
            context["null_count"] = int(df.isnull().sum().sum())
            context["duplicate_count"] = int(df.duplicated().sum())
            context["columns"] = list(df.columns)
            
            # Ubah pengisian nilai kosong dan konversi ke list of lists (agar cocok dengan perulangan baris-kolom)
            df_filled = df.head(8).fillna("-")
            context["preview"] = df_filled.values.tolist()

        except Exception as e:
            messages.error(request, f"Gagal membaca file: {str(e)}")

    return render(request, "preprocessing/bersih.html", context)


@login_required
def preprocessing_normalisasi(request):
    last_file = request.session.get("last_uploaded_file")
    context = {
        "has_file": False,
        "filename": None,
        "numeric_columns": [],
        "preview_before": None,
        "preview_after": None,
    }

    if last_file and os.path.exists(last_file):
        try:
            if last_file.endswith(".xlsx"):
                df = pd.read_excel(last_file)
            else:
                df = pd.read_csv(last_file, encoding="latin1")

            df.columns = df.columns.str.strip()

            # Ambil kolom numerik
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if not numeric_cols:
                # Coba konversi beberapa kolom umum
                for col in ["Qty", "Total Harga", "Frekuensi"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            context["has_file"] = True
            context["filename"] = os.path.basename(last_file)
            context["numeric_columns"] = numeric_cols

            if numeric_cols:
                preview_cols = numeric_cols[:4]  # ambil max 4 kolom
                context["preview_before"] = df[preview_cols].head(6).round(2).to_dict(orient="records")

                # Min-Max Normalization
                df_norm = df[preview_cols].copy()
                for col in preview_cols:
                    min_val = df_norm[col].min()
                    max_val = df_norm[col].max()
                    if max_val - min_val != 0:
                        df_norm[col] = (df_norm[col] - min_val) / (max_val - min_val)
                    else:
                        df_norm[col] = 0
                context["preview_after"] = df_norm.head(6).round(4).to_dict(orient="records")

        except Exception as e:
            messages.error(request, f"Gagal membaca file: {str(e)}")

    return render(request, "preprocessing/normalisasi.html", context)


@login_required
def preprocessing_seleksi(request):
    last_file = request.session.get("last_uploaded_file")
    context = {
        "has_file": False,
        "filename": None,
        "all_columns": [],
        "recommended": ["Customer", "Qty", "Total Harga"],
    }

    if last_file and os.path.exists(last_file):
        try:
            if last_file.endswith(".xlsx"):
                df = pd.read_excel(last_file)
            else:
                df = pd.read_csv(last_file, encoding="latin1")

            df.columns = df.columns.str.strip()
            context["has_file"] = True
            context["filename"] = os.path.basename(last_file)
            context["all_columns"] = list(df.columns)

        except Exception as e:
            messages.error(request, f"Gagal membaca file: {str(e)}")

    return render(request, "preprocessing/seleksi.html", context)


@login_required
def preprocessing_outlier(request):
    last_file = request.session.get("last_uploaded_file")
    context = {
        "has_file": False,
        "filename": None,
        "outlier_info": [],
    }

    if last_file and os.path.exists(last_file):
        try:
            if last_file.endswith(".xlsx"):
                df = pd.read_excel(last_file)
            else:
                df = pd.read_csv(last_file, encoding="latin1")

            df.columns = df.columns.str.strip()

            # Deteksi outlier sederhana (IQR) pada kolom numerik
            numeric_cols = []
            for col in ["Qty", "Total Harga"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(
                        df[col].astype(str)
                        .str.replace("Rp", "", regex=False)
                        .str.replace(".", "", regex=False)
                        .str.replace(",", "", regex=False),
                        errors="coerce"
                    )
                    numeric_cols.append(col)

            outlier_info = []
            for col in numeric_cols:
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outliers = df[(df[col] < lower) | (df[col] > upper)]
                outlier_info.append({
                    "column": col,
                    "count": len(outliers),
                    "lower": round(lower, 2),
                    "upper": round(upper, 2),
                    "min": round(df[col].min(), 2),
                    "max": round(df[col].max(), 2),
                })

            context["has_file"] = True
            context["filename"] = os.path.basename(last_file)
            context["outlier_info"] = outlier_info

        except Exception as e:
            messages.error(request, f"Gagal membaca file: {str(e)}")

    return render(request, "preprocessing/outlier.html", context)

# ==========================================================
# VISUALISASI (terhubung data asli)
# ==========================================================

@login_required
def visualisasi_distribusi(request):
    last_history = ClusteringHistory.objects.filter(
        user=request.user, status="completed"
    ).order_by("-created_at").first()

    labels = []
    values = []

    if last_history:
        clusters = last_history.clusters.all().order_by("cluster_label")
        for c in clusters:
            name = c.label_name if getattr(c, "label_name", None) else f"Cluster {c.cluster_label + 1}"
            # Coba beberapa kemungkinan field jumlah anggota
            count = getattr(c, "member_count", None)
            if count is None:
                try:
                    count = c.members.count()
                except:
                    count = 0
            labels.append(name)
            values.append(count)

    if not labels:
        labels = ["Belum ada data"]
        values = [0]

    return render(request, "visualisasi/distribusi.html", {
        "cluster_labels": labels,
        "cluster_values": values,
        "has_data": bool(last_history and labels[0] != "Belum ada data"),
        "history": last_history,
    })


@login_required
def visualisasi_scatter(request):
    last_history = ClusteringHistory.objects.filter(
        user=request.user, status="completed"
    ).order_by("-created_at").first()

    # Data untuk scatter (contoh struktur)
    scatter_data = {
        "tinggi": [],
        "sedang": [],
        "rendah": [],
    }

    if last_history:
        for cluster in last_history.clusters.all():
            label = (cluster.label_name or "").lower()
            members = getattr(cluster, "members", None)
            if members:
                for m in members.all()[:30]:  # batasi biar tidak terlalu banyak
                    point = {
                        "x": getattr(m, "monetary", getattr(m, "total_omzet", 50)),
                        "y": getattr(m, "frequency", getattr(m, "frekuensi", 5)),
                    }
                    if "tinggi" in label or "high" in label:
                        scatter_data["tinggi"].append(point)
                    elif "sedang" in label or "potential" in label:
                        scatter_data["sedang"].append(point)
                    else:
                        scatter_data["rendah"].append(point)

    return render(request, "visualisasi/scatter.html", {
        "scatter_data": scatter_data,
        "has_data": bool(last_history),
    })


@login_required
def visualisasi_heatmap(request):
    # Heatmap biasanya butuh data mentah, untuk sementara tetap tampilkan contoh yang bagus
    return render(request, "visualisasi/heatmap.html", {
        "has_data": True
    })


@login_required
def visualisasi_elbow(request):
    # Elbow Method biasanya dihitung saat proses clustering.
    # Untuk sementara kita tampilkan grafik contoh yang sudah bagus.
    return render(request, "visualisasi/elbow.html", {
        "has_data": True
    })


@login_required
def visualisasi_radar(request):
    last_history = ClusteringHistory.objects.filter(
        user=request.user, status="completed"
    ).order_by("-created_at").first()

    radar_labels = ["Recency", "Frequency", "Monetary", "Qty", "Loyalty"]
    datasets = []

    if last_history:
        colors = [
            ("#16a34a", "rgba(22,163,74,0.2)"),
            ("#0ea5e9", "rgba(14,165,233,0.2)"),
            ("#f59e0b", "rgba(245,158,11,0.2)"),
            ("#8b5cf6", "rgba(139,92,246,0.2)"),
        ]
        for i, cluster in enumerate(last_history.clusters.all().order_by("cluster_label")):
            name = cluster.label_name or f"Cluster {cluster.cluster_label + 1}"
            # Nilai contoh berdasarkan urutan (bisa diganti statistik asli nanti)
            base = 90 - (i * 25)
            data = [
                max(20, base - 40),   # Recency (semakin kecil semakin bagus)
                max(20, base),        # Frequency
                max(20, base + 5),    # Monetary
                max(20, base - 5),    # Qty
                max(20, base - 10),   # Loyalty
            ]
            color = colors[i % len(colors)]
            datasets.append({
                "label": name,
                "data": data,
                "borderColor": color[0],
                "backgroundColor": color[1],
            })

    return render(request, "visualisasi/radar.html", {
        "radar_labels": radar_labels,
        "radar_datasets": datasets,
        "has_data": bool(datasets),
    })