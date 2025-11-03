from rest_framework import serializers
from . import models
from decimal import Decimal



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
        
    def validate(self, data):
        data['category'] = data['category'].strip().lower()
        data['item'] = data['item'].strip().lower()
        data['transaction_type'] = data['transaction_type'].strip().lower()
        if data.get('transaction_type') not in ['expense','income']:
            raise serializers.ValidationError('You Have To Input Valid Transaction Type')
        if data.get('category').isdigit():
            raise serializers.ValidationError("Category Can't Be A Number")
        if data.get('item').isdigit():
            raise serializers.ValidationError("Item Can't Be A Number")
        return data
    
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
            raise serializers.ValidationError('You Have To Include Valid Category')
        return data


    def create(self, validated_data):
        validated_data['user'] = self.context.get('request').user
        return super().create(validated_data)