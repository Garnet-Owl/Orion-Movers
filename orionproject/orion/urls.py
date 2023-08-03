from django.urls import path
from . import views

app_name = 'your_app_name'  # Replace 'your_app_name' with the actual name of your app

urlpatterns = [
    path('create_user/', views.create_user, name='create_user'),
    path('create_mover/', views.create_mover, name='create_mover'),
    path('match_movers/', views.match_movers, name='match_movers'),
    path('order_moving_service/', views.order_moving_service, name='order_moving_service'),
    path('process_payment/<int:order_id>/', views.process_payment, name='process_payment'),
    path('rate_mover/<int:mover_id>/', views.rate_mover, name='rate_mover'),
    path('search_movers/', views.search_movers, name='search_movers'),
    # Add any additional URLs you have defined in your views.py here
]
