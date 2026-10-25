from django.db import transaction
from rest_framework import views, permissions, response, status

from network.models import Nodes
from .utils import normalize_name, normalized_nodes


class NodesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        nodes = Nodes.objects.all()
        nodes = [{'id': node.id, 'name': node.name} for node in nodes]
        return response.Response(nodes, status=status.HTTP_200_OK)

    def post(self, request):
        name = request.data.get('name')
        name = str(name) if name is not None else None
        normalized_name = normalize_name(name)
        if not normalized_name or normalized_nodes().filter(normalized_name=normalized_name).exists():
            return response.Response({'error': 'Name missing or duplicate'}, status=status.HTTP_400_BAD_REQUEST)
        
        node = Nodes.objects.create(name=name, created_by=request.user, updated_by=request.user)
        return response.Response({'id': node.id, 'name': node.name}, status=status.HTTP_201_CREATED)


class NodeDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, node_id):
        try:
            node = Nodes.objects.get(id=node_id)
            with transaction.atomic():
                node.delete()
            return response.Response({'message': 'Node deleted successfully'}, status=status.HTTP_200_OK)
        except Nodes.DoesNotExist:
            return response.Response({'error': 'Node not found'}, status=status.HTTP_404_NOT_FOUND)
