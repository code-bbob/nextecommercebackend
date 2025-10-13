from rest_framework import serializers
from .models import Product, Comment, Repliess, ProductImage, Rating, Series,Emi, ProductAttribute
from django.contrib.auth.models import User

class ReplySerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField() #yo garexi i can define serializers for user by myself i.e. user ko kun attribute pathaune vanera
    comment = serializers.PrimaryKeyRelatedField(read_only=True)
    user_dp = serializers.SerializerMethodField()
    class Meta:
        model = Repliess
        fields = ['user', 'comment','text','published_date','user_dp']
    def get_user(self, obj):
        return obj.user.name
    
    def get_user_dp(self, obj):
        request = self.context.get('request')
        if obj.user.dp and request:
            return request.build_absolute_uri(f"/media/{obj.user.dp}")



class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField() #yo garexi i can define serializers for user by myself i.e. user ko kun attribute pathaune vanera
    product = serializers.PrimaryKeyRelatedField(read_only=True)
    replies = ReplySerializer(many=True, read_only=True)
    user_dp = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = '__all__'

    def get_user(self, obj):
        return obj.user.name
    
    def get_user_dp(self, obj):
        request = self.context.get('request')
        if obj.user.dp:
            return request.build_absolute_uri(f"/media/{obj.user.dp}")
    
class ProductImageSerializer(serializers.ModelSerializer):
    color_name = serializers.SerializerMethodField()
    hex = serializers.SerializerMethodField()
    class Meta:
        model = ProductImage
        fields = ['image','color','color_name','hex']

    def get_color_name(self, obj):
        return obj.color.name if obj.color else None

    def get_hex(self, obj):
        return obj.color.hex if obj.color else None

class RatingSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only = True)
    product = serializers.PrimaryKeyRelatedField(read_only =True)
    image = serializers.SerializerMethodField()
    user_dp = serializers.SerializerMethodField(read_only = True)
    
    class Meta:
        model = Rating
        fields = '__all__'

    def get_user(self, obj):
        return obj.user.name
    
    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None
    def get_user_dp(self, obj):
        request = self.context.get('request')
        if obj.user.dp:
            return request.build_absolute_uri(f"/media/{obj.user.dp}")
        
class ProductAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = ['attribute', 'value']
    
class ProductSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many = True, read_only = True)
    brandName = serializers.SerializerMethodField()
    ratings = serializers.SerializerMethodField()
    category = serializers.StringRelatedField()
    sub_category = serializers.StringRelatedField()
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = '__all__'
        

    def get_ratings(self,obj):
        request = self.context.get('request')
        stats = {}
        ratings = Rating.objects.filter(product=obj)
        if ratings.exists():
            total_ratings = ratings.count()
            #show how many stars ratings were rated acc to each star
            rating_dict = {1:0, 2:0, 3:0, 4:0, 5:0}
            for rating in ratings:
                rating_dict[rating.rating] += 1
            avg_rating = sum(rating.rating for rating in ratings) / len(ratings)
            avg_rating = round(avg_rating, 1)
            stats = {'total_ratings': total_ratings, 'rating_dict': rating_dict, 'avg_rating': avg_rating}
        else:
            stats = {'total_ratings': 0, 'rating_dict': {1:0, 2:0, 3:0, 4:0, 5:0}, 'avg_rating':0}
        serializer = RatingSerializer(ratings, many=True, context={'request': request})
        return {"stats":stats, "data":serializer.data}
    
    def get_brandName(self, obj):
        return obj.brand.name

class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = ['id','name']

class EmiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emi
        fields = '__all__'