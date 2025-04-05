from django.contrib import admin
from .models import Product, Comment, Repliess, ProductImage, Rating, Brand,Series, Category, SubCategory, ProductAttribute, PredefinedAttribute
from import_export.admin import ImportExportModelAdmin
from .resources import ProductResource, ProductAttributeResource, ProductImageResource, BrandResource, SeriesResource, CategoryResource, SubCategoryResource, PredefinedAttributeResource
# Register your models here.

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0

class ProductImageAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    model = ProductImage
    resource_class = ProductImageResource

class RatingInLine(admin.TabularInline):
    model = Rating
    extra = 0

class BrandAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    model = Brand
    resource_class = ProductAttributeResource

class SeriesAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    model = Series
    resource_class = ProductAttributeResource

class CategoryAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    model = Category
    resource_class = ProductAttributeResource

class SubCategoryAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    model = SubCategory
    resource_class = ProductAttributeResource

class PredefinedAttributeAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    model = PredefinedAttribute
    resource_class = ProductAttributeResource


class ProductAttributeAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    model = ProductAttribute
    resource_class = ProductAttributeResource

class AttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 0

class ProductsAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    inlines = [AttributeInline,ProductImageInline, RatingInLine]
    resource_class = ProductResource


admin.site.register(Product,ProductsAdmin)
admin.site.register(Comment)
admin.site.register(Repliess)
admin.site.register(Brand, BrandAdmin)
admin.site.register(ProductImage, ProductImageAdmin)
admin.site.register(Series,SeriesAdmin)
admin.site.register(Category,CategoryAdmin)
admin.site.register(SubCategory,SubCategoryAdmin)
admin.site.register(PredefinedAttribute,PredefinedAttributeAdmin)
admin.site.register(ProductAttribute, ProductAttributeAdmin)