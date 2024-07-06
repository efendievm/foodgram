from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from recipes.models import Ingredient, Recipe, RecipeIngredient, Tag
from .utils import Base64ImageField

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=150,
        validators=[
            RegexValidator(regex=r'^[\w.@+-]+\Z'),
            UniqueValidator(queryset=User.objects.all()),
        ],
    )
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('password')
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        return user

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'password'
        )


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(read_only=True, default=False)
    avatar = serializers.SerializerMethodField(read_only=True)

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None

    class Meta:
        model = User
        fields = (
            'id',
            'avatar',
            'is_subscribed',
            'username',
            'first_name',
            'last_name',
            'email',
        )


class UserSetAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    def to_representation(self, data):
        return {'avatar': data.avatar.url}

    class Meta:
        model = User
        fields = ('avatar',)


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(read_only=True)

    def get_image(self, obj):
        return obj.image.url if obj.image else None

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserWithRecipesSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField()

    def get_recipes(self, obj):
        query = obj.recipes.all()
        recipes_limit = self.context['request'].GET.get('recipes_limit')
        if recipes_limit:
            query = query[: int(recipes_limit)]
        serializer = RecipeMinifiedSerializer(query, many=True)
        return serializer.data

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipeingredient_set', read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.BooleanField(
        read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True, default=False)
    image = Base64ImageField()
    name = serializers.CharField(max_length=256)
    text = serializers.CharField()
    cooking_time = serializers.IntegerField(min_value=1)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = instance.image.url if instance.image else None
        return data

    def get_fields(self, *args, **kwargs):
        fields = super().get_fields()
        if self.context['request'].method in ['PUT', 'PATCH']:
            fields['image'].required = False
        return fields

    def validate(self, attrs):
        self.__validate_tags(attrs)
        self.__validate_ingredients(attrs)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.__set_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        for key, val in validated_data.items():
            setattr(instance, key, val)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.__set_ingredients(instance, ingredients)
        instance.save()
        return instance

    def __set_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create(
            objs=[
                RecipeIngredient(
                    recipe=recipe,
                    ingredient_id=ingredient['id'],
                    amount=ingredient['amount'],
                )
                for ingredient in ingredients
            ]
        )

    def __validate_tags(self, attrs):
        tags = self.initial_data.get('tags')
        if not tags:
            raise ValidationError('Отсутствует поле тэгов')
        if len(set(tags)) != len(tags):
            raise ValidationError('Тэги повторяются')
        if len(Tag.objects.filter(id__in=tags)) != len(tags):
            raise ValidationError('Один или несколько тэгов не существуют')
        attrs['tags'] = tags

    def __validate_ingredients(self, attrs):
        ingredients = self.initial_data.get('ingredients')
        if not ingredients:
            raise ValidationError('Отсутствует поле ингредиентов')
        invalid_data = filter(
            lambda ingredient: (
                not ingredient.get('id') or not ingredient.get('amount')
            ),
            ingredients,
        )
        if list(invalid_data):
            raise ValidationError('Некорректный формат данных об ингредиентах')
        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        if len(set(ingredient_ids)) != len(ingredient_ids):
            raise ValidationError('Ингредиенты повторяются')
        invalid_data = filter(
            lambda ingredient: ingredient.get('amount') < 1, ingredients
        )
        if list(invalid_data):
            raise ValidationError(
                'Количество ингредиентов должно быть больше 1'
            )
        existing_ingredients = (
            Ingredient.objects
            .filter(id__in=ingredient_ids)
            .count()
        )
        if existing_ingredients != len(ingredient_ids):
            raise ValidationError(
                'Один или несколько ингредиентов не существуют'
            )
        attrs['ingredients'] = ingredients

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'name',
            'text',
            'ingredients',
            'image',
            'cooking_time',
            'author',
            'is_favorited',
            'is_in_shopping_cart',
        )
