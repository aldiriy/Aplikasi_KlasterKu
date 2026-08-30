def assign_cluster_label(avg_monetary, avg_frequency, avg_recency, all_clusters_stats):
    """
    Memberikan label otomatis ke cluster berdasarkan statistik.
    all_clusters_stats = list of dict, contoh:
    [
        {'monetary': 5000000, 'frequency': 12, 'recency': 5},
        {'monetary': 1000000, 'frequency': 3, 'recency': 40},
        ...
    ]
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
    }
    return recommendations.get(label_name, "Analisis lebih lanjut diperlukan.")


def get_cluster_color(label_name):
    colors = {
        "High Value": "#16a34a",   # hijau
        "Potential": "#0ea5e9",    # biru
        "At Risk": "#f59e0b",      # oranye
        "Low Value": "#94a3b8",    # abu-abu
    }
    return colors.get(label_name, "#0ea5e9")