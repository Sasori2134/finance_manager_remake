from rest_framework import serializers
from . import models
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

user = get_user_model()


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Transaction

        fields = [
            'pk',
            'created_at',
            'category',
            'item',
            'price',
            'transaction_type'
        ]


class BudgetSerializer(serializers.ModelSerializer):
    spent = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    remaining = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    class Meta:
        model = models.Monthly_budget

        fields = [
            'pk',
            'budget',
            'spent',
            'remaining',
            'category',
            'created_at'
        ]


class RecurringBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Recurring_bill
        fields = [
            'pk',
            'category',
            'amount',
            'payment_due',
            'item',
            'transaction_type',
            'created_at'
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[
            RegexValidator(
                regex=r'^(?=.*[A-Z])(?=(?:.*\d){3,}).+$', 
                message="You should have at least one uppercase character and at least 3 numbers in password")
        ])

    class Meta:
        model = user
        fields = [
            'email',
            'password'
        ]
    
    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError({"password" : e.messages})
        return value


class DashboardSerializer(serializers.Serializer):
    period_choices = [
        ('1m', '1M'),
        ('2m', '2M'),
        ('3m', '3M')
    ]
    period = serializers.ChoiceField(period_choices)


class ChangepasswordinputSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only = True)
    new_password = serializers.CharField(write_only = True,  validators = [RegexValidator(
                regex=r'^(?=.*[A-Z])(?=(?:.*\d){3,}).+$', 
                message="You should have at least one uppercase character and at least 3 numbers in password")
        ])

    def validate(self, data):
        user = self.context['request'].user
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        if not user.check_password(current_password):
            raise serializers.ValidationError({"password" : 'Wrong password!'})
        elif new_password == current_password:
            raise serializers.ValidationError({'password' : "Your new password can't be same as your current password"})
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            raise serializers.ValidationError({"password" : e.messages})