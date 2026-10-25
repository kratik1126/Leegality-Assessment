from django.contrib import admin

from network.models import Edges, Nodes, Routes

# Register your models here.
admin.site.register(Nodes)
admin.site.register(Edges)
admin.site.register(Routes)