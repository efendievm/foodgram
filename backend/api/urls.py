from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (IngredientsViewSet, get_recipe, 
                    RecipeViewSet, TagViewSet, UserViewSet)

router = SimpleRouter()
router.register(r"ingredients", IngredientsViewSet, basename="ingredients")
router.register(r"recipes", RecipeViewSet, basename="recipes")
router.register(r"tags", TagViewSet, basename="tags")
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls)),
    path("s/<str:short_link>", get_recipe),
    path("auth/", include("djoser.urls.authtoken")),
]
