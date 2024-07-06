from django.db.models import F, Sum

from recipes.models import RecipeIngredient


def get_shopping_list(user):
    ings = (
        RecipeIngredient.objects.filter(recipe__shopping_cart=user)
        .values(
            name=F("ingredient__name"),
            measurement_unit=F("ingredient__measurement_unit"),
        )
        .annotate(amount=Sum("amount"))
    )
    shopping_list = [f"Список покупок {user.username}"]
    shopping_list.extend(
        f'{ing["name"]}: {ing["amount"]} {ing["measurement_unit"]}'
        for ing in ings
    )
    shopping_list = "\n".join(shopping_list)
    return shopping_list
