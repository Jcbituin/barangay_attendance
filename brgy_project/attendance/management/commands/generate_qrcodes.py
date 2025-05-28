from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import UserQRCode
import qrcode
from io import BytesIO
from django.core.files import File


class Command(BaseCommand):
    help = 'Generate QR codes for users without one'

    def handle(self, *args, **kwargs):
        users_without_qr = User.objects.filter(userqrcode__isnull=True)
        for user in users_without_qr:
            qr_data = f"UserID:{user.id} Username:{user.username}"
            qr_img = qrcode.make(qr_data)
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)
            qr_code_obj = UserQRCode(user=user)
            qr_code_obj.qr_code_image.save(f'user_{user.id}_qr.png', File(buffer), save=True)
            self.stdout.write(f'QR code generated for {user.username}')

