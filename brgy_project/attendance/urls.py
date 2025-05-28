from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('signup/', views.signup, name='signup'),
    
    path('login/', auth_views.LoginView.as_view(template_name='attendance/landing.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('dashboard_redirect/', views.dashboard_redirect, name='dashboard_redirect'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),

    path('attendance/', views.user_attendance, name='user_attendance'),
    path('attendance/scan_qr/', views.scan_qr, name='scan_qr'),
    path('attendance/mark_attendance/', views.mark_attendance, name='mark_attendance'),

    path('profile/', views.profile, name='profile'),

    path('dashboard/admin/users/', views.user_management, name='user_management'),
    path('dashboard/admin/users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('dashboard/admin/users/deactivate/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('dashboard/admin/users/reactivate/<int:user_id>/', views.reactivate_user, name='reactivate_user'),
    path('dashboard/admin/users/delete/<int:user_id>/', views.delete_user, name='delete_user'),

    path('dashboard/admin/attendance/', views.attendance_management, name='attendance_management'),
    path('dashboard/admin/qr_management/', views.qr_management, name='qr_management'),
    path('dashboard/admin/scan_qr/', views.admin_scan_qr, name='admin_scan_qr'),

    path('admin-attendance/', views.admin_attendance, name='admin_attendance'),

    path('dashboard/admin/attendance/export/excel/', views.export_attendance_excel, name='export_attendance_excel'),
]
