from . import models


class CategoryCreateUpdateMixin:
    def resolve_category(self, validated_data):
        category = validated_data.get("category")

        if category is None:
            return validated_data

        category_name = category.get("category")

        if category_name is None:
            return validated_data

        category_obj, _ = models.CategoryModel.objects.get_or_create(
            category=category_name
        )

        validated_data["category"] = category_obj
        return validated_data
