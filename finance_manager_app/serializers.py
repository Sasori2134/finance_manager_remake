from rest_framework import serializers
from . import models
from decimal import Decimal
from django.conf import settings
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model

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

    def create(self, validated_data):
        validated_data['user'] = self.context.get('request').user
        return super().create(validated_data)


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Monthly_budget

        fields = [
            'pk',
            'budget',
            'category',
            'created_at'
        ]

    def validate(self, data):
        user = self.context['request'].user
        data['category'] = data['category'].strip().lower()
        if models.Monthly_budget.objects.filter(user_id=user, category=data.get('category')).exists():
            raise serializers.ValidationError('Category Already Exists')
        if data.get('category').isdigit():
            raise serializers.ValidationError(
                'You Have To Include Valid Category')
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context.get('request').user
        return super().create(validated_data)


class RecurringBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Recurring_bill
        fields = [
            'pk',
            'category',
            'amount',
            'recurring_bill_type',
            'item',
            'transaction_type',
            'created_at'
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context.get('request').user
        return super().create(validated_data)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[
            RegexValidator(
                regex=r'^(?=.*[A-Z])(?=(?:.*\d){3,}).+$', message="You should have at least one uppercase character and at least 3 numbers in password")
        ])

    class Meta:
        model = user
        fields = [
            'email',
            'password'
        ]
