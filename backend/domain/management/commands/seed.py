import os
from csv import DictReader
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from domain.models import (Ingredient, Recipe, RecipeIngredient, RecipeTag,
                           Subscription, Tag, UserFavoriteRecipes,
                           UserShoppingCart)

User = get_user_model()


class Command(BaseCommand):
    help = "Loads data"

    def handle(self, *args, **options):
        self.clear_database_data()
        self.load_users()
        self.load_ingredients()
        self.load_tags()
        self.load_recipes()
        self.load_recipe_ingredients()
        self.load_recipe_tags()
        self.load_user_favorite_recipes()
        self.load_user_shopping_cart()
        self.load_subscriptions()

    def clear_database_data(self):
        models_to_clear = [
            User,
            Ingredient,
            Recipe,
            RecipeIngredient,
            RecipeTag,
            Subscription,
            Tag,
            UserFavoriteRecipes,
            UserShoppingCart,
        ]
        for model_class in models_to_clear:
            model_class.objects.all().delete()

    def try_save(self, obj, name):
        try:
            obj.save()
        except Exception as ex:
            print(f"Unable to load object {name}. Error: {repr(ex)}")

    def open_file(self, name):
        return open(
            os.path.join(settings.SEEDDATA_DIR, f"{name}.csv"),
            encoding="utf-8"
        )

    def load_users(self):
        print("Loading Users")
        password = settings.SEED_USERS_PASSWORD
        i = 1
        for row in DictReader(self.open_file("users")):
            user = User(
                id=i,
                username=row["username"],
                email=f'{row["username"]}@gmail.com',
                first_name=row["first_name"],
                last_name=row["last_name"],
                avatar=os.path.join(f'avatars/{row["username"]}.png'),
            )
            user.set_password(password)
            self.try_save(user, "user")
            i += 1
        User.objects.create_superuser(
            settings.ADMIN_USERNAME,
            settings.ADMIN_EMAIL,
            settings.ADMIN_PASSWORD
        )

    def load_ingredients(self):
        print("Loading Ingredients")
        i = 1
        for row in DictReader(self.open_file("ingredients")):
            ingredient = Ingredient(
                id=i,
                name=row["name"],
                measurement_unit=row["measurement_unit"]
            )
            self.try_save(ingredient, "ingredient")
            i += 1

    def load_tags(self):
        print("Loading Tags")
        i = 1
        for row in DictReader(self.open_file("tags")):
            tag = Tag(
                id=i,
                name=row["name"],
                slug=row["slug"]
            )
            self.try_save(tag, "tag")
            i += 1

    def load_recipes(self):
        print("Loading Recipes")
        i = 1
        for row in DictReader(self.open_file("recipes")):
            recipe = Recipe(
                id=i,
                name=row["name"],
                cooking_time=row["cooking_time"],
                author_id=row["author"],
                text=row["text"],
                image=f'recipes/{row["image_name"]}.png',
            )
            self.try_save(recipe, "recipe")
            i += 1

    def load_recipe_ingredients(self):
        print("Loading Recipe Ingredients")
        i = 1
        for row in DictReader(self.open_file("recipe_ingredients")):
            recipe_ingredient = RecipeIngredient(
                id=i,
                recipe_id=row["recipe"],
                ingredient_id=row["ingredient"],
                amount=row["amount"],
            )
            self.try_save(recipe_ingredient, "recipe_ingredient")
            i += 1

    def load_recipe_tags(self):
        print("Loading Recipe Tags")
        i = 1
        for row in DictReader(self.open_file("recipe_tags")):
            recipe_tag = RecipeTag(
                id=i,
                recipe_id=row["recipe"],
                tag_id=row["tag"])
            self.try_save(recipe_tag, "recipe_tag")
            i += 1

    def load_user_favorite_recipes(self):
        print("Loading User favorite recipes")
        i = 1
        for row in DictReader(self.open_file("users_favorite_recipes")):
            user_favorite_recipe = UserFavoriteRecipes(
                id=i,
                user_id=row["user"],
                recipe_id=row["recipe"]
            )
            self.try_save(user_favorite_recipe, "user_favorite_recipe")
            i += 1

    def load_user_shopping_cart(self):
        print("Loading Users favorite recipes")
        i = 1
        for row in DictReader(self.open_file("users_shopping_carts")):
            user_shopping_cart = UserShoppingCart(
                id=i,
                user_id=row["user"],
                recipe_id=row["recipe"]
            )
            self.try_save(user_shopping_cart, "user_shopping_cart")
            i += 1

    def load_subscriptions(self):
        print("Loading Users shopping carts")
        i = 1
        for row in DictReader(self.open_file("subscriptions")):
            subscription = Subscription(
                id=i,
                user_id=row["user"],
                following_id=row["following"]
            )
            self.try_save(subscription, "subscription")
            i += 1
