from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include


from core import views
from core.views import (
    dashboard,
    upload_data,
    run_clustering,
    clustering_result,
    download_report,
    login_view,
    register,
    logout_view,
    change_password,
    profile,
)

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload-data/', views.upload_data, name='upload_data'),
    path('upload-data/hapus/<int:pk>/', views.hapus_upload, name='hapus_upload'),   # ← tambah ini

    path('run-clustering/', views.run_clustering, name='run_clustering'),
    path('clustering-result/', views.clustering_result, name='clustering_result'),
    path('download-report/', views.download_report, name='download_report'),

    # Master Customer
    path('master-customer/', views.master_customer, name='master_customer'),
    path('master-customer/tambah/', views.tambah_customer, name='tambah_customer'),
    path('master-customer/edit/<int:pk>/', views.edit_customer, name='edit_customer'),
    path('master-customer/hapus/<int:pk>/', views.hapus_customer, name='hapus_customer'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    path("profile/", views.profile, name="profile"),

    path("master-barang/", views.master_barang, name="master_barang"),
    path("tambah-barang/", views.tambah_barang, name="tambah_barang"),
    path("edit-barang/<int:pk>/", views.edit_barang, name="edit_barang"),
    path("hapus-barang/<int:pk>/", views.hapus_barang, name="hapus_barang"),
    path("barang-masuk/<int:pk>/", views.barang_masuk, name="barang_masuk"),
    path("detail-barang/<int:pk>/", views.detail_barang, name="detail_barang"),
    path("upload-stok-barang/", views.upload_stok_barang, name="upload_stok_barang"),

    # Master Label
    path("master-label/", views.master_label, name="master_label"),
    path("tambah-label/", views.tambah_label, name="tambah_label"),
    path("edit-label/<int:pk>/", views.edit_label, name="edit_label"),
    path("hapus-label/<int:pk>/", views.hapus_label, name="hapus_label"),
    path("label-masuk/<int:pk>/", views.label_masuk, name="label_masuk"),
    path("detail-label/<int:pk>/", views.detail_label, name="detail_label"),
    path('label/upload/', views.upload_label, name='upload_label'),

# Master Kemasan
    path("master-kemasan/", views.master_kemasan, name="master_kemasan"),
    path("tambah-kemasan/", views.tambah_kemasan, name="tambah_kemasan"),
    path("edit-kemasan/<int:pk>/", views.edit_kemasan, name="edit_kemasan"),
    path("hapus-kemasan/<int:pk>/", views.hapus_kemasan, name="hapus_kemasan"),
    path("kemasan-masuk/<int:pk>/", views.kemasan_masuk, name="kemasan_masuk"),
    path("detail-kemasan/<int:pk>/", views.detail_kemasan, name="detail_kemasan"),
    path('kemasan/upload/', views.upload_kemasan, name='upload_kemasan'),

    path('clustering/history/', views.clustering_history, name='clustering_history'),
    path('clustering/history/<int:pk>/', views.clustering_detail, name='clustering_detail'),
    path('clustering/history/<int:pk>/cluster/<int:cluster_id>/', views.cluster_members, name='cluster_members'),
    path('clustering/export/<int:pk>/', views.export_clustering_excel, name='export_clustering_excel'),
    path('clustering/status/<int:pk>/', views.clustering_status, name='clustering_status'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)