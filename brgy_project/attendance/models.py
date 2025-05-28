from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()  # just date without time
    time_in_am = models.TimeField(null=True, blank=True)
    time_out_am = models.TimeField(null=True, blank=True)
    time_in_pm = models.TimeField(null=True, blank=True)
    time_out_pm = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'date')  # one attendance record per user per day

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class UserQRCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    qr_code_image = models.ImageField(upload_to='qr_codes/', null=True, blank=True)

    def __str__(self):
        return f"QR Code for {self.user.username}"
