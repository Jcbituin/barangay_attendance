from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserQRCode
import qrcode
from io import BytesIO
from django.core.files import File
from django.core.files.base import ContentFile


@receiver(post_save, sender=User)
def create_user_qr_code(sender, instance, created, **kwargs):
    if created:
        if not UserQRCode.objects.filter(user=instance).exists():
            # Use consistent format for all users:
            qr_data = f"user:{instance.username}"
            qr_img = qrcode.make(qr_data)
            
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)
            
            qr_code_obj = UserQRCode(user=instance)
            qr_code_obj.qr_code_image.save(f'user_{instance.id}_qr.png', ContentFile(buffer.getvalue()), save=True)
