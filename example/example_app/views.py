from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView

from .models import Item, ItemActivity
from .forms import ItemForm


class ItemDetailView(DetailView):
    model = Item


class ItemUpdateView(UpdateView):
    model = Item
    form_class = ItemForm

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save(activity=ItemActivity(
            description=form.cleaned_data['description'],
            author=self.request.user if self.request.user.is_authenticated() else None
        ))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('example_app:view', args=(self.object.id,))


class ItemCreateView(CreateView):
    model = Item
    form_class = ItemForm

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save(activity=ItemActivity(
            description=form.cleaned_data['description'],
            author=self.request.user if self.request.user.is_authenticated() else None
        ))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('example_app:view', args=(self.object.id,))


class ItemListView(ListView):
    model = Item

    def get_context_data(self, **kwargs):
        context = super(ItemListView, self).get_context_data(**kwargs)
        return context
