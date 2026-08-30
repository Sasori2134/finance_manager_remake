from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, RegexValidator
from rest_framework import serializers

from finance_manager_app.custom_mixins import CategoryCreateUpdateMixin

from . import models

user = get_user_model()


# TODO: delete this later
# class TransactionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.Transaction

#         fields = [
#             "pk",
#             "category",
#             "recurring_bill",
#             "item",
#             "price",
#             "transaction_type",
#             "created_at",
#         ]


class categorySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.CategoryModel

        fields = ["pk", "category"]


class RecurringBillSerializer(serializers.ModelSerializer, CategoryCreateUpdateMixin):
    transaction_type = serializers.CharField(read_only=True)
    paid = serializers.BooleanField(read_only=True, required=False)
    category = categorySerializer()

    class Meta:
        model = models.Recurring_bill

        fields = [
            "pk",
            "category",
            "price",
            "payment_due",
            "item",
            "transaction_type",
            "paid",
            "created_at",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise ValidationError(message="amount must be greater than 0")
        return value

    def create(self, validated_data):
        validated_data = self.resolve_category(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self.resolve_category(validated_data)
        return super().update(instance, validated_data)


# class RecurringBillGetListSerializer(serializers.ModelSerializer):
#     transaction_type = serializers.CharField(read_only=True)

#     class Meta:
#         model = models.Recurring_bill
#         fields = [
#             "pk",
#             "category",
#             "amount",
#             "payment_due",
#             "item",
#             "transaction_type",
#             "created_at",
#         ]


class TransactionSerializer(serializers.ModelSerializer, CategoryCreateUpdateMixin):
    category = categorySerializer()
    recurring_bill = RecurringBillSerializer(read_only=True)

    class Meta:
        model = models.Transaction

        fields = [
            "pk",
            "category",
            "recurring_bill",
            "item",
            "price",
            "transaction_type",
            "created_at",
        ]

    def validate_price(self, value):
        if value <= 0:
            raise ValidationError(message="price must be greater than 0")
        return value

    def create(self, validated_data):
        validated_data = self.resolve_category(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self.resolve_category(validated_data)
        return super().update(instance, validated_data)


class BudgetSerializer(serializers.ModelSerializer, CategoryCreateUpdateMixin):
    spent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    remaining = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    category = categorySerializer()

    class Meta:
        model = models.Monthly_budget
        fields = [
            "pk",
            "budget",
            "spent",
            "remaining",
            "category",
            "created_at",
        ]

    def create(self, validated_data):
        validated_data = self.resolve_category(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self.resolve_category(validated_data)
        return super().update(instance, validated_data)

    def validate(self, attrs):
        user = self.context.get("request").user
        category = attrs.get("category")

        if category is None:
            return super().validate(attrs)

        category_name = category.get("category")

        category_user_exists = self.Meta.model.objects.filter(
            user=user, category__category=category_name
        ).exists()

        if category_user_exists:
            raise ValidationError(message="budget for this category already exists")
        return super().validate(attrs)

    def validate_budget(self, value):
        if value <= 0:
            raise ValidationError(message="budget must be greater than 0")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[
            RegexValidator(
                regex=r"^(?=.*[A-Z])(?=(?:.*\d){3,}).+$",
                message="You should have at least one uppercase character and at least 3 numbers in password",
            )
        ],
    )

    class Meta:
        model = user
        fields = ["email", "password"]

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})
        return value

    def save(self):
        created_user = user.objects.create_user(**self.validated_data)
        return created_user


class DashboardSerializer(serializers.Serializer):
    period_choices = [("1m", "1M"), ("2m", "2M"), ("3m", "3M")]
    period = serializers.ChoiceField(period_choices, required=False, default="1m")


class ChangepasswordinputSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True,
        validators=[
            RegexValidator(
                regex=r"^(?=.*[A-Z])(?=(?:.*\d){3,}).+$",
                message="You should have at least one uppercase character and at least 3 numbers in password",
            )
        ],
    )

    def validate(self, data):
        user = self.context["request"].user
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        if not user.check_password(current_password):
            raise serializers.ValidationError({"current_password": "Wrong password!"})
        elif new_password == current_password:
            raise serializers.ValidationError(
                {
                    "new_password": "Your new password can't be same as your current password"
                }
            )
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": e.messages})
        return data

    def save(self):
        user = self.context["request"].user
        new_password = self.validated_data.get("new_password")
        user.set_password(new_password)
        user.save()
        return user


class ForgotPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(validators=[EmailValidator("Invalid email")])

    # might add email check


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        validators=[
            RegexValidator(
                regex=r"^(?=.*[A-Z])(?=(?:.*\d){3,}).+$",
                message="You should have at least one uppercase character and at least 3 numbers in password",
            )
        ],
    )
    email = serializers.EmailField(validators=[EmailValidator("Invalid email")])

    def validate(self, data):
        new_password = data.get("password")
        user_instance = user.objects.filter(email=data.get("email"))
        if not user_instance.exists():
            raise serializers.ValidationError({"detail": "Email doesn't exist"})
        elif user_instance.first().check_password(new_password):
            raise serializers.ValidationError(
                {"detail": "You password can't be same as your current password"}
            )
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise ValidationError({"detail": e})
        return data

    def save(self):
        user_ins = user.objects.filter(email=self.validated_data.get("email")).first()

        new_password = self.validated_data.get("password")
        user_ins.set_password(new_password)

        user_ins.save(update_fields=["password"])
        return user_ins
