from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import Product, ProductImage, ProductAttribute, Category, Brand, Series,SubCategory,PredefinedAttribute, Color, Variant

class ProductResource(resources.ModelResource):
    product_id = fields.Field(attribute='product_id', column_name='product_id')
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name')
    )
    brand = fields.Field(
        column_name='brand',
        attribute='brand',
        widget=ForeignKeyWidget(Brand, 'name')
    )
    series = fields.Field(
        column_name='series',
        attribute='series',
        widget=ForeignKeyWidget(Series, 'name')
    )

    class Meta:
        model = Product
        import_id_fields = ['product_id']  # <-- important!
        fields = ('product_id', 'name', 'category', 'brand', 'series', 'price', 'description', 'published_date')

class ProductImageResource(resources.ModelResource):
    # Using ForeignKeyWidget for mapping the related Product model
    product = fields.Field(
        column_name='product_name', 
        attribute='product', 
        widget=ForeignKeyWidget(Product, 'name')  # Ensuring 'name' is unique or use 'product_id' if it's more reliable
    )
    # Use Field for custom handling of the image file
    image = fields.Field(attribute='image', column_name='image_file')

    class Meta:
        model = ProductImage
        fields = ('id', 'product', 'image')


class ProductAttributeResource(resources.ModelResource):
    # ForeignKeyWidget for referencing the product
    product = fields.Field(
        column_name='product_name', 
        attribute='product', 
        widget=ForeignKeyWidget(Product, 'name')  # Same note as above for unique identifier
    )
    # Mapping attributes and values
    attribute = fields.Field(attribute='attribute', column_name='attribute')
    value = fields.Field(attribute='value', column_name='value')

    class Meta:
        model = ProductAttribute
        fields = ('id', 'product', 'attribute', 'value')

class BrandResource(resources.ModelResource):
    class Meta:
        model = Brand
        fields = ('id', 'name')

class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        fields = ('id', 'name')

class SeriesResource(resources.ModelResource):
    class Meta:
        model = Series
        fields = '__all__'

class SubCategoryResource(resources.ModelResource):
    class Meta:
        model = SubCategory
        fields = '__all__'


class PredefinedAttributeResource(resources.ModelResource):
    class Meta:
        model = PredefinedAttribute
        fields = '__all__'

class ColorResource(resources.ModelResource):
    class Meta:
        model = Color
        fields = '__all__'

class VariantResource(resources.ModelResource):
    class Meta:
        model = Variant
        fields = '__all__'
