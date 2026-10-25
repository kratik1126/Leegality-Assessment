from rest_framework import views, permissions, response, status
from django.db import transaction

from network.models import Edges
from .utils import get_nodes_by_normalized_names, normalize_name


class EdgesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        edges = Edges.objects.all()
        edges = [{'id': edge.id, 'source': edge.source.name, 'destination': edge.destination.name, 'latency': edge.latency} for edge in edges]
        return response.Response(edges, status=status.HTTP_200_OK)

    def post(self, request):
        source = request.data.get('source')
        destination = request.data.get('destination')
        latency = request.data.get('latency')
        normalized_source = normalize_name(source)
        normalized_destination = normalize_name(destination)
        if latency is None or not isinstance(latency, (int, float)) or latency < 0:
            return response.Response({'error': 'latency <= 0'}, status=status.HTTP_400_BAD_REQUEST)
        if not normalized_source or not normalized_destination:
            return response.Response({'error': 'Source/destination missing'}, status=status.HTTP_400_BAD_REQUEST)
        if normalized_source == normalized_destination:
            return response.Response({'error': 'Source and destination names cannot be the same'}, status=status.HTTP_400_BAD_REQUEST)

        nodes_by_name = get_nodes_by_normalized_names(normalized_source, normalized_destination)
        source_node = nodes_by_name.get(normalized_source)
        destination_node = nodes_by_name.get(normalized_destination)

        if not source_node or not destination_node:
            return response.Response({'error': 'nodes not found'}, status=status.HTTP_404_NOT_FOUND)

        if Edges.objects.filter(source=source_node, destination=destination_node).exists():
            return response.Response({'error': 'duplicate edge'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            edge = Edges.objects.create(source=source_node, destination=destination_node, latency=latency, created_by=request.user, updated_by=request.user)
        return response.Response({'id': edge.id, 'source': edge.source.name, 'destination': edge.destination.name, 'latency': edge.latency}, status=status.HTTP_201_CREATED)


class EdgeDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, edge_id):
        try:
            edge = Edges.objects.get(id=edge_id)
            edge.delete()
            return response.Response({'message': 'Edge deleted successfully'}, status=status.HTTP_200_OK)
        except Edges.DoesNotExist:
            return response.Response({'error': 'Edge not found'}, status=status.HTTP_404_NOT_FOUND)
