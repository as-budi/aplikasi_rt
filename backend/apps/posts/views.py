from django.utils import timezone
from rest_framework import viewsets

from apps.core.models import audit
from apps.core.permissions import IsStaffOrReadOnly, is_staff_rt

from .models import Post
from .serializers import PostSerializer


class PostViewSet(viewsets.ModelViewSet):
    """Berita & kegiatan. Semua pengguna membaca; pengurus menulis."""

    serializer_class = PostSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ["type", "is_published"]

    def get_queryset(self):
        qs = Post.objects.select_related("author")
        if not is_staff_rt(self.request.user):
            qs = qs.filter(is_published=True)
        if self.request.query_params.get("upcoming"):
            qs = qs.filter(type=Post.Type.KEGIATAN, event_at__gte=timezone.now()).order_by("event_at")
        return qs

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        audit(self.request.user, "buat_posting", post)

    def perform_update(self, serializer):
        post = serializer.save()
        audit(self.request.user, "ubah_posting", post)

    def perform_destroy(self, instance):
        audit(self.request.user, "hapus_posting", instance)
        instance.delete()
