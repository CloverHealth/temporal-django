from django.conf.urls import url

from . import views

app_name = 'example_app'

urlpatterns = [
    url(r'^$', views.ItemListView.as_view(), name='index'),
    url(r'^item/(?P<pk>\d+)$', views.ItemDetailView.as_view(), name='view'),
    url(r'^item/(?P<pk>\d+)/edit$', views.ItemUpdateView.as_view(), name='update'),
    url(r'^item/create$', views.ItemCreateView.as_view(), name='create'),
]
