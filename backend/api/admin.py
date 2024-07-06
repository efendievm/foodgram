from django.contrib import admin
from django.contrib.auth import get_user_model
from recipes.models import (Ingredient, Recipe, RecipeIngredient, RecipeTag,
                           Subscription, Tag, UserFavoriteRecipes,
                           UserShoppingCart)

User = get_user_model()


class IngredientAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "measurement_unit")
    search_fields = ("name",)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "author", "get_favorited_count")
    search_fields = (
        "author__first_name",
        "author__first_name",
        "author__username",
        "name",
    )
    list_filter = ("tags",)

    def get_favorited_count(self, obj):
        return UserFavoriteRecipes.objects.filter(recipe=obj).count()

    get_favorited_count.short_description = "Число добавлений в избранное"


class UserAdmin(admin.ModelAdmin):
    list_display = ("pk", "username", "first_name", "last_name", "email")
    search_fields = ("first_name", "email")


admin.site.register(User, UserAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(RecipeIngredient)
admin.site.register(RecipeTag)
admin.site.register(Subscription)
admin.site.register(Tag)
admin.site.register(UserFavoriteRecipes)
admin.site.register(UserShoppingCart)
