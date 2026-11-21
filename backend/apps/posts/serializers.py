from rest_framework import serializers

from .models import Post


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True, default=None)

    class Meta:
        model = Post
        fields = [
            "id", "type", "title", "body", "event_at", "location", "is_pinned", "is_published",
            "published_at", "author_name", "created_at", "updated_at",
        ]
        read_only_fields = ["published_at", "created_at", "updated_at"]

    def validate(self, attrs):
        post_type = attrs.get("type", getattr(self.instance, "type", None))
        event_at = attrs.get("event_at", getattr(self.instance, "event_at", None))
        if post_type == Post.Type.KEGIATAN and not event_at:
            raise serializers.ValidationError({"event_at": "Kegiatan wajib punya tanggal dan jam."})
        return attrs
