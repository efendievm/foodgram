import base64
from random import choice
from string import ascii_letters, digits

from django.core.files.base import ContentFile
from django_filters import FilterSet, ModelMultipleChoiceFilter, NumberFilter
from rest_framework import filters, serializers
from rest_framework.pagination import PageNumberPagination

from recipes.models import Recipe, ShortLink, Tag


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name="temp." + ext)
        return super().to_internal_value(data)


class Pagination(PageNumberPagination):
    page_query_param = "page"
    page_size_query_param = "limit"
    page_size = 6


class SearchFilter(filters.SearchFilter):
    search_param = "name"


class RecipeFilterSet(FilterSet):
    is_favorited = NumberFilter(field_name="is_favorited")
    is_in_shopping_cart = NumberFilter(field_name="is_in_shopping_cart")
    author = NumberFilter(field_name="author__pk")
    tags = ModelMultipleChoiceFilter(
        field_name="tags__slug",
        to_field_name="slug",
        queryset=Tag.objects.all()
    )

    class Meta:
        model = Recipe
        fields = ("author", "is_favorited", "is_in_shopping_cart")


def get_or_create_short_link(recipe_id):
    chars = ascii_letters + digits
    links = list(ShortLink.objects.values("link"))
    link = __create_random_link(chars)
    while link in links:
        link = __create_random_link(chars)
    ShortLink.objects.create(recipe_id=recipe_id, link=link)
    return link


def __create_random_link(chars):
    return "".join([choice(chars) for _ in range(5)])
