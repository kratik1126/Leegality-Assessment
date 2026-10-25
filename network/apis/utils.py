from django.db.models.functions import Lower, Trim

from network.models import Nodes


def normalize_name(name):
    """Return a trimmed, lowercase name, preserving None for missing values."""
    return str(name).strip().lower() if name is not None else None


def normalized_nodes():
    """Return nodes annotated with the same normalized name used by API inputs."""
    return Nodes.objects.annotate(normalized_name=Lower(Trim('name')))


def get_nodes_by_normalized_names(*names):
    """Fetch matching nodes in one query, keyed by their normalized names."""
    return {
        node.normalized_name: node
        for node in normalized_nodes().filter(normalized_name__in=names)
    }
