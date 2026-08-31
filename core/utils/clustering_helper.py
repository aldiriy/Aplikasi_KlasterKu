def assign_cluster_label(avg_monetary, avg_frequency, avg_recency, all_clusters_stats):
    """
    Memberikan label otomatis ke cluster berdasarkan statistik.
    """
    if not all_clusters_stats:
        return "Cluster"

    max_monetary = max(c['monetary'] for c in all_clusters_stats) or 1
    max_frequency = max(c['frequency'] for c in all_clusters_stats) or 1

    # High Value
    if avg_monetary >= max_monetary * 0.7 and avg_frequency >= max_frequency * 0.6:
        return "High Value"

    # Potential
    if avg_monetary >= max_monetary * 0.4 and avg_frequency >= max_frequency * 0.4:
        return "Potential"

    # At Risk
    if avg_monetary >= max_monetary * 0.3 and avg_frequency < max_frequency * 0.3:
        return "At Risk"

    return "Low Value"


def get_recommendation(label_name):
    recommendations = {
        "High Value": (
            "Pertahankan dengan program loyalitas, diskon eksklusif, "
            "dan layanan prioritas. Fokus pada retensi customer."
        ),
        "Potential": (
            "Lakukan upselling & cross-selling. Berikan penawaran produk "
            "premium dan tingkatkan frekuensi pembelian."
        ),
        "At Risk": (
            "Segera follow-up oleh sales. Berikan penawaran khusus "
            "untuk mengaktifkan kembali transaksi."
        ),
        "Low Value": (
            "Kurangi biaya pemasaran. Fokus pada efisiensi. "
            "Pertimbangkan campaign edukasi produk."
        ),
        "Tinggi": (
            "Prioritas UTAMA. Siapkan stok bahan baku lebih banyak dan pastikan ketersediaan. "
            "Customer ini sering membeli dan dalam jumlah besar."
        ),
        "Sedang": (
            "Prioritas SEDANG. Pantau stok secara berkala. Siapkan stok sesuai pola rata-rata."
        ),
        "Rendah": (
            "Prioritas RENDAH. Stok disiapkan minimal. Fokus pada efisiensi gudang."
        ),
    }
    return recommendations.get(label_name, "Analisis lebih lanjut diperlukan.")


def get_cluster_color(label_name):
    colors = {
        "Tinggi": "#16a34a",      # hijau
        "Sedang": "#0ea5e9",      # biru
        "Rendah": "#94a3b8",      # abu-abu
        "High Value": "#16a34a",
        "Potential": "#0ea5e9",
        "At Risk": "#f59e0b",
        "Low Value": "#94a3b8",
    }
    return colors.get(label_name, "#0ea5e9")