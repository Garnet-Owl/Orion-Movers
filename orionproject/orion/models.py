from django.contrib.gis.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.geos import Point

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Add any other fields you want in your CustomUser model

class Mover(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    vehicle = models.CharField(max_length=100)
    identity_document = models.FileField(upload_to='identity_documents/')
    identity_verified = models.BooleanField(default=False)
    background_check = models.BooleanField(default=False)
    rating = models.FloatField(default=0.0)  # Average rating from customer ratings

class Customer(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    location = models.PointField()

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    mover = models.ForeignKey(Mover, on_delete=models.CASCADE)
    start_address = models.CharField(max_length=200)
    end_address = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default='pending')  # You can use choices for different status types
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)

class Rating(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    mover = models.ForeignKey(Mover, on_delete=models.CASCADE)
    score = models.IntegerField()
    comment = models.TextField()
