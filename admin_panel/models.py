from django.db import models
from django.contrib.auth.models import User
import uuid
from django.db.models.signals import post_save  
from django.dispatch import receiver 
import random  
import string  



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_blocked = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)  
    phone = models.CharField(max_length=15, blank=True, null=True)
    referral_code = models.CharField(max_length=10, unique=True, blank=True, null=True) 
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')  

    
    
    
    def save(self, *args, **kwargs):  
        if not self.referral_code: 
            self.referral_code = self.generate_referral_code()  
        super().save(*args, **kwargs)  

    def generate_referral_code(self):  
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))  
        while UserProfile.objects.filter(referral_code=code).exists():  
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))  
        return code  
    
    

    def __str__(self):
        return f"Profile of {self.user.username}"
    
    
    

    
    