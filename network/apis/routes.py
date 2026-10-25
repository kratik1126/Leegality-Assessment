import heapq
from collections import defaultdict
from datetime import date

from django.db import transaction
from django.db.models import Prefetch
from django.db.models.functions import Lower, Trim
from rest_framework import views, permissions, response, status

from network.models import Edges, Routes, RouteEdges
from .utils import get_nodes_by_normalized_names, normalize_name


class ShortestRouteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def find_shortest_path(self, source_id, destination_id):
        graph = defaultdict(list)
        for edge in Edges.objects.select_related('source', 'destination'):
            graph[edge.source_id].append(edge)

        distances = {source_id: 0}
        previous_edge = {}
        heap = [(0, source_id)]
        visited = set()

        while heap:
            distance, node_id = heapq.heappop(heap)
            if node_id in visited:
                continue
            visited.add(node_id)
            if node_id == destination_id:
                break
            for edge in graph[node_id]:
                new_distance = distance + edge.latency
                if new_distance < distances.get(edge.destination_id, float('inf')):
                    distances[edge.destination_id] = new_distance
                    previous_edge[edge.destination_id] = edge
                    heapq.heappush(heap, (new_distance, edge.destination_id))

        if destination_id not in visited:
            return None, None

        path_edges = []
        node_id = destination_id
        while node_id != source_id:
            edge = previous_edge[node_id]
            path_edges.append(edge)
            node_id = edge.source_id
        path_edges.reverse()
        return distances[destination_id], path_edges

    def post(self, request):
        source = request.data.get('source')
        destination = request.data.get('destination')
        normalized_source = normalize_name(source)
        normalized_destination = normalize_name(destination)
        if not normalized_source or not normalized_destination:
            return response.Response({'error': 'Source/destination missing'}, status=status.HTTP_400_BAD_REQUEST)
        if normalized_source == normalized_destination:
            return response.Response({'error': 'Source and destination names cannot be the same'}, status=status.HTTP_400_BAD_REQUEST)

        nodes_by_name = get_nodes_by_normalized_names(normalized_source, normalized_destination)
        source_node = nodes_by_name.get(normalized_source)
        destination_node = nodes_by_name.get(normalized_destination)
        if not source_node or not destination_node:
            return response.Response({'error': 'nodes not found'}, status=status.HTTP_404_NOT_FOUND)

        total_latency, path_edges = self.find_shortest_path(source_node.id, destination_node.id)
        if path_edges is None:
            return response.Response({'error': 'No path found'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            route = Routes.objects.filter(source=source_node, destination=destination_node).order_by('total_latency').first()
            if route is None or total_latency < route.total_latency:
                route = Routes.objects.create(
                    source=source_node, destination=destination_node, total_latency=total_latency,
                    created_by=request.user, updated_by=request.user,
                )
                RouteEdges.objects.bulk_create(
                    RouteEdges(route=route, edge=edge, position=i) for i, edge in enumerate(path_edges)
                )

            path_edges = [route_edge.edge for route_edge in route.route_edges.select_related('edge__destination')]
            total_latency = route.total_latency 

        path = [source_node.name] + [edge.destination.name for edge in path_edges]
        return response.Response({'total_latency': total_latency, 'path': path}, status=status.HTTP_200_OK)


class RouteHistoryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def parse_date(self, value):
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    def get(self, request):
        source = normalize_name(request.query_params.get('source'))
        destination = normalize_name(request.query_params.get('destination'))
        limit = request.query_params.get('limit')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        routes = Routes.objects.select_related('source', 'destination').prefetch_related(
            Prefetch('route_edges', queryset=RouteEdges.objects.select_related('edge__destination'))
        ).order_by('-created_at')

        if source:
            routes = routes.annotate(normalized_source=Lower(Trim('source__name'))).filter(normalized_source=source)
        if destination:
            routes = routes.annotate(normalized_destination=Lower(Trim('destination__name'))).filter(normalized_destination=destination)

        if date_from:
            date_from = self.parse_date(date_from)
            if date_from is None:
                return response.Response({'error': 'date_from must be YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
            routes = routes.filter(created_at__date__gte=date_from)
        if date_to:
            date_to = self.parse_date(date_to)
            if date_to is None:
                return response.Response({'error': 'date_to must be YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
            routes = routes.filter(created_at__date__lte=date_to)
        if date_from and date_to and date_from > date_to:
            return response.Response({'error': 'date_from cannot be after date_to'}, status=status.HTTP_400_BAD_REQUEST)

        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                limit = 0
            if limit <= 0:
                return response.Response({'error': 'limit must be a positive integer'}, status=status.HTTP_400_BAD_REQUEST)
            routes = routes[:limit]

        history = [
            {
                'id': route.id,
                'source': route.source.name,
                'destination': route.destination.name,
                'total_latency': route.total_latency,
                'path': [route.source.name] + [route_edge.edge.destination.name for route_edge in route.route_edges.all()],
                'created_at': route.created_at,
            }
            for route in routes
        ]
        return response.Response(history, status=status.HTTP_200_OK)
