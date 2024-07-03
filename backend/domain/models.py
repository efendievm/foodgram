from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Count, Exists, OuterRef, Prefetch


class DetailedUserManager(BaseUserManager):
    def is_subscribed(self, user):
        user = user if user and user.is_authenticated else None
        return self.annotate(
            is_subscribed=Exists(Subscription.objects.filter(
                user=user,
                following_id=OuterRef('pk'),
            )))

    def subscribed_with_recipes(self, user):
        recipes = Prefetch(
            'recipes',
            queryset=Recipe.objects.order_by('-pub_date'))
        return self.is_subscribed(user).filter(
            is_subscribed=True).prefetch_related(recipes).annotate(
                recipes_count=Count('recipes'))


class CustomUserAccountManager(BaseUserManager):
    def create_superuser(self, username, email, password, **extrafields):
        extrafields.setdefault('role', 'admin')
        user = self.create_user(username, email, password, **extrafields)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user

    def create_user(self, username, email, password, **extrafields):
        if not email:
            raise ValueError('Email address is required!')
        if not username:
            raise ValueError('Username is required!')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extrafields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user


class User(AbstractUser):
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        null=True,
        blank=True)
    email = models.EmailField('Email', unique=True)
    role = models.CharField(default='user', max_length=10, blank=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def create_superuser(self, username, email, password, **extrafields):
        extrafields.setdefault('role', 'admin')
        user = self.create_user(username, email, password, **extrafields)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserAccountManager()
    detailed = DetailedUserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.username})'


class Tag(models.Model):
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('Уникальный слаг', unique=True)

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField('Название', max_length=128)
    measurement_unit = models.CharField('Единица измерения', max_length=64)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class DetailedRecipeManager(models.Manager):
    def annotate_extra_info(self, user):
        query = self.prefetch_related(
            'tags',
            Prefetch('recipeingredient_set', RecipeIngredient.detailed.all()))
        user = user if user.is_authenticated else None
        author = Prefetch('author', queryset=User.detailed.is_subscribed(user))
        return query.prefetch_related(author).annotate(
            is_favorited=Exists(UserFavoriteRecipes.objects.filter(
                recipe_id=OuterRef('pk'), user=user)),
            is_in_shopping_cart=Exists(UserShoppingCart.objects.filter(
                recipe_id=OuterRef('pk'), user=user)))


class Recipe(models.Model):
    name = models.CharField('Название', max_length=256)
    text = models.TextField('Описание')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)
    image = models.ImageField(upload_to='recipes/', null=True, blank=True)
    cooking_time = models.SmallIntegerField(
        'Время приготовления (в минутах)')
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='recipes')
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэги',
        through='RecipeTag')
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Список ингредиентов',
        through='RecipeIngredient')
    shopping_cart = models.ManyToManyField(
        User,
        verbose_name='В списке покупок пользователей',
        through='UserShoppingCart',
        related_name='recipes_in_shopping_cart')
    favorited = models.ManyToManyField(
        User,
        verbose_name='В списке избранного пользователей',
        through='UserFavoriteRecipes',
        related_name='favorited_recipes')

    objects = models.Manager()
    detailed = DetailedRecipeManager()

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class DetaiedRecipeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('ingredient')


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт')
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент')
    amount = models.SmallIntegerField('Количество')

    objects = models.Manager()
    detailed = DetaiedRecipeManager()

    class Meta:
        unique_together = ("recipe", "ingredient")
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецептов'

    def __str__(self):
        return f'{self.recipe}: {self.ingredient}, {self.amount}'


class RecipeTag(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт')
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name='Тэг')

    class Meta:
        unique_together = ("recipe", "tag")
        verbose_name = 'Тэг рецепта'
        verbose_name_plural = 'Тэги рецептов'

    def __str__(self):
        return f'{self.recipe}: {self.tag}'


class UserFavoriteRecipes(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь')

    class Meta:
        unique_together = ("recipe", "user")
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'

    def __str__(self):
        return f'{self.user}: {self.recipe}'


class UserShoppingCart(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь')

    class Meta:
        unique_together = ("recipe", "user")
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f'{self.user}: {self.recipe}'


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик')
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Пользователь')

    class Meta:
        unique_together = ("user", "following")
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user}: {self.following}'


class ShortLink(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    link = models.CharField(max_length=5)
