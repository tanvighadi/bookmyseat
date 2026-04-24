from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from movies.views import admin_dashboard  # import your custom dashboard view

urlpatterns = [
    # ✅ Custom Admin Dashboard (must come first)
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),

    # Django's built-in admin
    path('admin/', admin.site.urls),

    # User-related routes
    path('users/', include('users.urls')),

    # Movies app routes
    path('movies/', include('movies.urls')),

    # Homepage → show movie list directly
    path('', include('users.urls')),   # root handled by users app
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
