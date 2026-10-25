from django.urls import path

from network import apis


urlpatterns = [
    path('nodes/', apis.NodesView.as_view(), name='nodes-list'),
    path('nodes/<int:node_id>/', apis.NodeDeleteView.as_view(), name='node-delete'),
    path('edges/', apis.EdgesView.as_view(), name='edges-list'),
    path('edges/<int:edge_id>/', apis.EdgeDeleteView.as_view(), name='edge-delete'),
    path('routes/shortest/', apis.ShortestRouteView.as_view(), name='shortest-route'),
    path('routes/history/', apis.RouteHistoryView.as_view(), name='route-history'),
]
