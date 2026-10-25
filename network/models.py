from django.conf import settings
from django.db import models


class GenericModel(models.Model):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+',)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Nodes(GenericModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Node'
        verbose_name_plural = 'Nodes'


class Edges(GenericModel):
    source = models.ForeignKey(Nodes, on_delete=models.CASCADE, related_name='source_edges')
    destination = models.ForeignKey(Nodes, on_delete=models.CASCADE, related_name='destination_edges')
    latency = models.FloatField()

    def __str__(self):
        return f"{self.source} -> {self.destination} ({self.latency})"

    class Meta:
        verbose_name = 'Edge'
        verbose_name_plural = 'Edges'


class Routes(GenericModel):
    source = models.ForeignKey(Nodes, on_delete=models.CASCADE, related_name='source_routes')
    destination = models.ForeignKey(Nodes, on_delete=models.CASCADE, related_name='destination_routes')
    path = models.ManyToManyField(Edges, through='RouteEdges', related_name='routes')
    total_latency = models.FloatField()

    def __str__(self):
        return f"{self.source} -> {self.destination} ({self.total_latency})"

    class Meta:
        verbose_name = 'Route'
        verbose_name_plural = 'Routes'


class RouteEdges(models.Model):
    route = models.ForeignKey(Routes, on_delete=models.CASCADE, related_name='route_edges')
    edge = models.ForeignKey(Edges, on_delete=models.CASCADE)
    position = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.route} #{self.position}: {self.edge}"

    class Meta:
        verbose_name = 'Route Edge'
        verbose_name_plural = 'Route Edges'
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(fields=['route', 'position'], name='unique_route_position'),
        ]