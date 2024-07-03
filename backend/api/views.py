from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from domain.models import (Ingredient, Recipe, RecipeIngredient, Subscription,
                           Tag, UserFavoriteRecipes, UserShoppingCart)

from .permissions import IsAuthorOrReadOnly
from .serializers import (IngredientSerializer, RecipeMinifiedSerializer,
                          RecipeSerializer, TagSerializer,
                          UserCreateSerializer, UserSerializer,
                          UserSetAvatarSerializer, UserWithRecipesSerializer)
from .utils import (Pagination, RecipeFilterSet, SearchFilter,
                    get_or_create_short_link)

User = get_user_model()


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (SearchFilter,)
    search_fields = ("^name",)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    pagination_class = Pagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilterSet

    def get_queryset(self):
        return Recipe.detailed.annotate_extra_info(self.request.user).order_by(
            "-pub_date"
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_permissions(self):
        if self.action in ["favorite", "shopping_cart"]:
            self.permission_classes = (IsAuthenticated,)
        else:
            self.permission_classes = (IsAuthorOrReadOnly,)
        return super().get_permissions()

    @action(detail=True, methods=["post", "delete"])
    def favorite(self, request, *args, **kwargs):
        return self.__handle_favorites_shopping_cart(
            request, kwargs["pk"], UserFavoriteRecipes, "избранных"
        )

    @action(detail=True, methods=["post", "delete"])
    def shopping_cart(self, request, *args, **kwargs):
        return self.__handle_favorites_shopping_cart(
            request, kwargs["pk"], UserShoppingCart, "корзине"
        )

    @action(detail=True, url_path="get-link", methods=["get"])
    def get_link(self, request, *args, **kwargs):
        get_object_or_404(Recipe, pk=kwargs["pk"])
        link = get_or_create_short_link(kwargs["pk"])
        link = f'{request.META["HTTP_HOST"]}/{link}'
        return Response(status=status.HTTP_200_OK, data={"short-link": link})

    @action(detail=False, methods=["get"])
    def download_shopping_cart(self, request, *args, **kwargs):
        ings = (
            RecipeIngredient.objects.filter(recipe__shopping_cart=request.user)
            .values(
                name=F("ingredient__name"),
                measurement_unit=F("ingredient__measurement_unit"),
            )
            .annotate(amount=Sum("amount"))
        )
        shopping_list = [f"Список покупок {request.user.username}"]
        shopping_list.extend(
            f'{ing["name"]}: {ing["amount"]} {ing["measurement_unit"]}'
            for ing in ings
        )
        shopping_list = "\n".join(shopping_list)
        filename = "shopping_list.txt"
        response = HttpResponse(
            shopping_list,
            content_type="text.txt; charset=utf-8"
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    def __handle_favorites_shopping_cart(self, request, pk, model_cls, target):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == "DELETE":
            try:
                to_delete = model_cls.objects.get(
                    user=request.user,
                    recipe=recipe
                )
                to_delete.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except model_cls.DoesNotExist:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data=f"Данный рецепт не был в {target}",
                )

        _, created = model_cls.objects.get_or_create(
            user=request.user,
            recipe=recipe
        )
        if not created:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data=f"Данный рецепт уже в {target}"
            )
        return Response(
            status=status.HTTP_201_CREATED,
            data=RecipeMinifiedSerializer(recipe).data
        )


class UserViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    pagination_class = Pagination

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "create"]:
            self.permission_classes = (AllowAny,)
        else:
            self.permission_classes = (IsAuthenticated,)
        return super().get_permissions()

    def get_queryset(self):
        if self.action in ["subscriptions", "subscribe"]:
            return User.detailed.subscribed_with_recipes(
                self.request.user
            ).all()
        return User.detailed.is_subscribed(self.request.user).all()

    @action(detail=False, methods=["get"])
    def me(self, request):
        user = self.get_queryset().get(id=request.user.id)
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def set_password(self, request, *args, **kwargs):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.request.user.set_password(serializer.data["new_password"])
        self.request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, url_path="me/avatar", methods=["put", "delete"])
    def avatar(self, request, *args, **kwargs):
        if request.method == "DELETE":
            request.user.avatar = None
            request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = UserSetAvatarSerializer(
            data=request.data,
            instance=request.user
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def subscriptions(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = UserWithRecipesSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post", "delete"])
    def subscribe(self, request, *args, **kwargs):
        following = get_object_or_404(User, pk=kwargs["pk"])
        if request.method == "DELETE":
            try:
                following = Subscription.objects.get(
                    user=request.user, following=following
                )
                following.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Subscription.DoesNotExist:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data="Нет подписки на данного пользователя",
                )
        if following == request.user:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data="Подписка на себя запрещена"
            )
        _, created = Subscription.objects.get_or_create(
            user=request.user, following=following
        )
        if not created:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data="Вы уже подписаны на этго пользователя",
            )
        following = self.get_queryset().get(pk=following.pk)
        return Response(
            status=status.HTTP_201_CREATED,
            data=UserWithRecipesSerializer(
                following, context={"request": request}
            ).data,
        )
