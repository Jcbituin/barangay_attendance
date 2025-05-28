from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.timezone import now, localtime, localdate
from django.utils import timezone
from django.urls import reverse
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.files import File
from django.template.loader import get_template
import qrcode
from io import BytesIO
import base64
import logging
from datetime import date, time
from .models import Profile, Attendance, UserQRCode
from .forms import ProfileForm
from django.template.loader import render_to_string
from django.contrib.admin.views.decorators import staff_member_required
import openpyxl

logger = logging.getLogger(__name__)


def landing(request):
    return render(request, 'attendance/landing.html')


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return render(request, 'attendance/signup.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return render(request, 'attendance/signup.html')

        user = User.objects.create_user(username=username, password=password1)
        user.save()

        messages.success(request, "Account created successfully! Please log in.")
        return redirect('landing')

    return render(request, 'attendance/signup.html')


def is_admin(user):
    return user.is_superuser or user.is_staff


def admin_required(view_func):
    return login_required(user_passes_test(is_admin)(view_func))


@login_required
def dashboard_redirect(request):
    if is_admin(request.user):
        return redirect('admin_dashboard')
    return redirect('dashboard')


@login_required
def dashboard(request):
    today = timezone.localdate()
    user = request.user

    if request.method == 'POST':
        attendance, created = Attendance.objects.get_or_create(user=user, date=today)

        current_time = timezone.localtime(timezone.now()).time()

        if time(6, 0) <= current_time <= time(11, 59) and not attendance.time_in_am:
            attendance.time_in_am = current_time
            attendance.save()
            messages.success(request, "AM Time In recorded.")
        elif time(12, 0) <= current_time <= time(12, 59) and not attendance.time_out_am:
            attendance.time_out_am = current_time
            attendance.save()
            messages.success(request, "AM Time Out recorded.")
        elif time(13, 0) <= current_time <= time(17, 59) and not attendance.time_in_pm:
            attendance.time_in_pm = current_time
            attendance.save()
            messages.success(request, "PM Time In recorded.")
        elif time(18, 0) <= current_time <= time(21, 0) and not attendance.time_out_pm:
            attendance.time_out_pm = current_time
            attendance.save()
            messages.success(request, "PM Time Out recorded.")
        else:
            messages.info(request, "Attendance for this time slot already recorded or outside recording hours.")

        return redirect('dashboard')

    attendance_record = Attendance.objects.filter(user=user).order_by('-date')

    return render(request, 'attendance/dashboard.html', {
        'attendance_record': attendance_record,
        'today': today,
    })


@login_required
def user_attendance(request):
    qr_data = f"user:{request.user.username}"

    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    context = {
        'qr_code_base64': img_str,
        'qr_data': qr_data,
    }
    return render(request, 'attendance/user_attendance.html', context)


@login_required
def profile(request):
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            updated_profile = form.save(commit=False)
            updated_profile.user = request.user
            updated_profile.save()

            if updated_profile.email and updated_profile.email != request.user.email:
                request.user.email = updated_profile.email
                request.user.save()

            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    if profile:
        return render(request, 'attendance/profile_view.html', {'profile': profile})
    return render(request, 'attendance/profile_form.html', {'form': form})


@admin_required
def admin_dashboard(request):
    today = localtime(now()).date()
    total_users = User.objects.count()
    attendance_today = Attendance.objects.filter(date=today).count()

    attendance_list = Attendance.objects.select_related('user').order_by('-date')
    paginator = Paginator(attendance_list, 20)
    page = request.GET.get('page', 1)

    try:
        attendance_page = paginator.page(page)
    except PageNotAnInteger:
        attendance_page = paginator.page(1)
    except EmptyPage:
        attendance_page = paginator.page(paginator.num_pages)

    context = {
        'total_users': total_users,
        'attendance_today': attendance_today,
        'attendance_page': attendance_page,
    }

    return render(request, 'attendance/admin_dashboard.html', context)


@login_required
def download_qr(request):
    qr_data = f"user:{request.user.username}"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    response = HttpResponse(content_type="image/png")
    response['Content-Disposition'] = 'attachment; filename="qr_code.png"'
    img.save(response)
    return response


@login_required
def scan_qr(request):
    return render(request, 'attendance/scan_qr.html')


@csrf_exempt
def mark_attendance(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."})

    qr_data = request.POST.get("qr_data", "")
    logger.info(f"Received QR data: {qr_data}")

    if not qr_data.startswith("user:"):
        return JsonResponse({"success": False, "message": "Invalid QR code format."})

    username = qr_data.split("user:")[1]
    logger.info(f"Extracted username: {username}")

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.warning(f"User not found: {username}")
        return JsonResponse({"success": False, "message": "User not found."})

    today = date.today()
    current_time = timezone.localtime().time()

    attendance, created = Attendance.objects.get_or_create(user=user, date=today)
    logger.info(f"Attendance record {'created' if created else 'found'} for {user.username} on {today}")

    MORNING_START = time(8, 0)
    MORNING_END = time(12, 0)
    AFTERNOON_START = time(13, 0)
    AFTERNOON_END = time(17, 0)

    if MORNING_START <= current_time <= MORNING_END:
        if not attendance.time_in_am:
            attendance.time_in_am = current_time
            attendance.save()
            logger.info(f"Recorded Time In (AM) for {user.username} at {current_time}")
            return JsonResponse({"success": True, "message": "Time In (AM) recorded."})
        elif not attendance.time_out_am:
            attendance.time_out_am = current_time
            attendance.save()
            logger.info(f"Recorded Time Out (AM) for {user.username} at {current_time}")
            return JsonResponse({"success": True, "message": "Time Out (AM) recorded."})
        else:
            return JsonResponse({"success": False, "message": "Morning attendance already recorded."})

    elif AFTERNOON_START <= current_time <= AFTERNOON_END:
        if not attendance.time_in_pm:
            attendance.time_in_pm = current_time
            attendance.save()
            logger.info(f"Recorded Time In (PM) for {user.username} at {current_time}")
            return JsonResponse({"success": True, "message": "Time In (PM) recorded."})
        elif not attendance.time_out_pm:
            attendance.time_out_pm = current_time
            attendance.save()
            logger.info(f"Recorded Time Out (PM) for {user.username} at {current_time}")
            return JsonResponse({"success": True, "message": "Time Out (PM) recorded."})
        else:
            return JsonResponse({"success": False, "message": "Afternoon attendance already recorded."})

    logger.info(f"Invalid time slot: {current_time} for user {user.username}")
    return JsonResponse({"success": False, "message": "Invalid time slot or already recorded."})


@admin_required
def user_management(request):
    users = User.objects.all()
    return render(request, 'attendance/user_management.html', {'users': users})


@admin_required
def attendance_management(request):
    attendance_management = Attendance.objects.select_related('user').order_by('user__username', '-date')

    context = {
        'attendance_management': attendance_management,
    }
    return render(request, 'attendance/attendance_management.html', context)


@admin_required
def qr_management(request):
    users = User.objects.all().select_related('userqrcode')
    return render(request, 'attendance/qr_management.html', {'users': users})


@admin_required
def edit_user(request, user_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.is_active = request.POST.get('is_active') == 'on'
        user.save()
        return redirect('user_management')

    return render(request, 'attendance/edit_user.html', {'user': user})


@admin_required
def delete_user(request, user_id):
    user_to_delete = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user_to_delete.delete()
        messages.success(request, f'User {user_to_delete.username} deleted successfully.')
        return redirect('user_management')
    return redirect('user_management')


@admin_required
def deactivate_user(request, user_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        user.is_active = False
        user.save()
        return redirect('user_management')

    return render(request, 'attendance/deactivate_user.html', {'user': user})


@admin_required
def reactivate_user(request, user_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        user.is_active = True
        user.save()
        return redirect('user_management')

    return render(request, 'attendance/reactivate_user.html', {'user': user})


@receiver(post_save, sender=User)
def create_user_qr_code(sender, instance, created, **kwargs):
    if created:
        if not hasattr(instance, 'userqrcode'):
            qr_data = f"UserID:{instance.id} Username:{instance.username}"
            qr_img = qrcode.make(qr_data)

            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)

            qr_code_obj = UserQRCode(user=instance)
            qr_code_obj.qr_code_image.save(f'user_{instance.id}_qr.png', File(buffer), save=True)


@admin_required
def admin_attendance(request):
    user = request.user
    qr_data = f"user:{user.username}"
    qr = qrcode.make(qr_data)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()

    attendance_management = Attendance.objects.select_related('user').order_by('-date')

    context = {
        'qr_code_base64': qr_code_base64,
        'attendance_management': attendance_management,
    }
    return render(request, 'attendance/admin_attendance.html', context)


@admin_required
def admin_attendance_view(request):
    today = localdate()
    todays_attendance = Attendance.objects.filter(date=today)

    context = {
        'attendance_management': todays_attendance,
    }
    return render(request, 'attendance/admin_attendance.html', context)


@login_required
@user_passes_test(is_admin)
def admin_scan_qr(request):
    return render(request, 'attendance/admin_scan_qr.html')


@login_required
def attendance_view(request):
    attendance_list = Attendance.objects.filter(user=request.user).order_by('-date')

    paginator = Paginator(attendance_list, 10)
    page = request.GET.get('page')

    try:
        attendance_page = paginator.page(page)
    except PageNotAnInteger:
        attendance_page = paginator.page(1)
    except EmptyPage:
        attendance_page = paginator.page(paginator.num_pages)

    return render(request, 'attendance/attendance_view.html', {
        'attendance_page': attendance_page,
    })

def export_attendance_excel(request):
    # Filter attendance for today
    today = date.today()
    attendance_records = Attendance.objects.filter(date=today)

    # Create an in-memory workbook and sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance for " + today.strftime("%Y-%m-%d")

    # Define headers
    headers = ["Username", "Date", "Time In (AM)", "Time Out (AM)", "Time In (PM)", "Time Out (PM)"]
    ws.append(headers)

    # Fill rows
    for record in attendance_records:
        ws.append([
            record.user.username,
            record.date.strftime("%Y-%m-%d"),
            record.time_in_am.strftime("%H:%M") if record.time_in_am else "",
            record.time_out_am.strftime("%H:%M") if record.time_out_am else "",
            record.time_in_pm.strftime("%H:%M") if record.time_in_pm else "",
            record.time_out_pm.strftime("%H:%M") if record.time_out_pm else "",
        ])

    # Prepare response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename=attendance_{today}.xlsx'

    # Save workbook to response
    wb.save(response)
    return response