from django.contrib import admin 
from .models import Customer, Permintaan, HasilClustering, UserProfile

admin.site.register(Customer) 
admin.site.register(Permintaan) 
admin.site.register(HasilClustering) 
admin.site.register(UserProfile)
