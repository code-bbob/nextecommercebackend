from django.shortcuts import render
from .models import Product,Comment
from math import ceil
from .serializers import ProductSerializer, CommentSerializer, ReplySerializer, RatingSerializer, SeriesSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import filters
from rest_framework import generics
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.pagination import PageNumberPagination
from django.db.models import Avg, Count
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from .serializers import EmiSerializer


# @api_view(['GET'])
# def getProduct(request):
#     prods = Product.objects.all()
#     serializer = ProductSerializer(prods, many=True)
#     return Response(serializer.data)                  
#function based view ma image ko right path janna only relative path like / media/shop/images bata janxa so class based use grya

class CustomPagination(PageNumberPagination):
    page_size = 16
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'results': data
        })


class GetProduct(APIView):
    def get(self, request, format=None):
        # Retrieve query parameters for filtering
        min_rating = request.query_params.get('min_rating')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        # Instead of a single 'ordering' value, expect multiple ordering parameters
        ordering_fields = request.query_params.getlist('ordering')
        brand = request.query_params.get('brand')
        # Base queryset annotated with average rating and rating count
        queryset = Product.objects.all().annotate(
            rating=Avg('ratings__rating'),
            ratings_count=Count('ratings')
        )
        
        # Apply filtering based on min_rating, min_price, and max_price if provided
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=float(min_rating))
            except (ValueError, TypeError):
                pass
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass
        if brand:
            try:
                queryset = queryset.filter(brand__name__icontains=brand)
            except (ValueError, TypeError,):
                pass
        # Apply ordering based on multiple parameters
        if ordering_fields:
            # If there's only one ordering field and it contains spaces, split it into parts.
            if len(ordering_fields) == 1 and " " in ordering_fields[0]:
                ordering_fields = ordering_fields[0].split()
            queryset = queryset.order_by(*ordering_fields)
        
        # Paginate the queryset using the custom pagination class
        paginator = CustomPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ProductSerializer(paginated_queryset, many=True, context={'request': request})
        
        # Return a paginated response
        return paginator.get_paginated_response(serializer.data)



class GetDealProduct(APIView):

    def get(self, request, format=None):
        # Retrieve query parameters for filtering
        min_rating = request.query_params.get('min_rating')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        # Instead of a single 'ordering' value, expect multiple ordering parameters
        ordering_fields = request.query_params.getlist('ordering')
        brand = request.query_params.get('brand')
        # Base queryset annotated with average rating and rating count
        queryset = Product.objects.filter(deal=True).annotate(
            rating=Avg('ratings__rating'),
            ratings_count=Count('ratings'),
        )
        
        # Apply filtering based on min_rating, min_price, and max_price if provided
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=float(min_rating))
            except (ValueError, TypeError):
                pass
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass
        if brand:
            try:
                queryset = queryset.filter(brand__name__icontains=brand)
            except (ValueError, TypeError,):
                pass
        # Apply ordering based on multiple parameters
        if ordering_fields:
            # If there's only one ordering field and it contains spaces, split it into parts.
            if len(ordering_fields) == 1 and " " in ordering_fields[0]:
                ordering_fields = ordering_fields[0].split()
            queryset = queryset.order_by(*ordering_fields)
        
        # Paginate the queryset using the custom pagination class
        paginator = CustomPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ProductSerializer(paginated_queryset, many=True, context={'request': request})
        
        # Return a paginated response
        return paginator.get_paginated_response(serializer.data)



class ApiSearch(generics.ListAPIView):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['product_id','name', 'description','brand__name','category__name','sub_category__name','series__name']
    ordering_fields = ['price']  # Add more ordering fields if needed
    pagination_class = CustomPagination

    def get_queryset(self):
        # Base queryset annotated with average rating and ratings count
        queryset = Product.objects.all().annotate(
            rating=Avg('ratings__rating'),
            ratings_count=Count('ratings')
        )   
        
        request = self.request
        # Retrieve query parameters for filtering
        min_rating = request.query_params.get('min_rating')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        brand = request.query_params.get('brand')
        ordering_fields = request.query_params.getlist('ordering')
        
        # Filter by minimum rating
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=float(min_rating))
            except (ValueError, TypeError):
                pass

        # Filter by minimum and maximum price
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        # Filter by brand (case-insensitive partial match)
        if brand:
            try:
                queryset = queryset.filter(brand__name__icontains=brand)
            except (ValueError, TypeError):
                pass

        # Apply ordering if provided. If a single ordering parameter contains spaces,
        # split it into multiple fields.
        if ordering_fields:
            if len(ordering_fields) == 1 and " " in ordering_fields[0]:
                ordering_fields = ordering_fields[0].split()
            queryset = queryset.order_by(*ordering_fields)
        
        return queryset


class BrandSearch(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['brandName']
    ordering_fields = ['price']

class ProductSearch(APIView):
    
    def get(self,request,id):
        try:
            product = Product.objects.get(pk=id)
        except Product.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product,context={"request": request})
        return Response(serializer.data)


        

class CatSearch(generics.ListAPIView):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['price', 'min_rating','rating','min_price','max_price']
    pagination_class = CustomPagination

    def get_queryset(self):
        cat = self.kwargs.get('name')
        series = self.kwargs.get('series')

        min_rating = self.request.query_params.get('min_rating')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        queryset = Product.objects.filter(category__name__iexact=cat)
        if series:
            queryset = queryset.filter(series__exact=series)
        queryset = queryset.annotate(
            rating=Avg('ratings__rating'),
            ratings_count=Count('ratings')
        )

        if min_rating:
            try:
                min_rating = float(min_rating)
                queryset = queryset.filter(rating__gte=min_rating)
            except (ValueError, TypeError):
                pass
        
        if min_price:
            try:
                min_price = float(min_price)
                queryset = queryset.filter(price__gte=min_price)
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                max_price = float(max_price)
                queryset = queryset.filter(price__lte=max_price)
            except (ValueError, TypeError):
                pass

        return queryset

    
class SubcatSearch(generics.ListAPIView):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['price', 'min_rating','rating','min_price','max_price']
    pagination_class = CustomPagination
    
    def get_queryset(self):
        sub_cat = self.kwargs.get('name')
        min_rating = self.request.query_params.get('min_rating')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        queryset = Product.objects.filter(sub_category__iexact=sub_cat)

        queryset = queryset.annotate(
            rating=Avg('ratings__rating'),
            ratings_count=Count('ratings')
        )
        
        # Filter by minimum rating if provided
        if min_rating:
            try:
                min_rating = float(min_rating)
                queryset = queryset.filter(rating__gte=min_rating)
            except (ValueError, TypeError):
                pass
        
        if min_price:
            try:
                min_price = float(min_price)
                queryset = queryset.filter(price__gte=min_price)
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                max_price = float(max_price)
                queryset = queryset.filter(price__lte=max_price)
            except (ValueError, TypeError):
                pass

        return queryset
    
class CatBrandSearch(generics.ListAPIView):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['price', 'min_rating','rating','min_price','max_price']
    pagination_class = CustomPagination

    def get_queryset(self):
        cat = self.kwargs.get('catname')
        brand = self.kwargs.get('brandname')

        
        min_rating = self.request.query_params.get('min_rating')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if brand:
            queryset = Product.objects.filter(category__name__iexact=cat, brand__name__iexact = brand)

        else:
            queryset = Product.objects.filter(category__iexact=cat)
        queryset = queryset.annotate(
            rating=Avg('ratings__rating'),
            ratings_count=Count('ratings')
        )

        if min_rating:
            try:
                min_rating = float(min_rating)
                queryset = queryset.filter(rating__gte=min_rating)
            except (ValueError, TypeError):
                pass
        
        if min_price:
            try:
                min_price = float(min_price)
                queryset = queryset.filter(price__gte=min_price)
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                max_price = float(max_price)
                queryset = queryset.filter(price__lte=max_price)
            except (ValueError, TypeError):
                pass

        return queryset
    
class SeriesSearch(generics.ListAPIView):
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['price']

    def get_queryset(self):
        cat = self.kwargs.get('catname')
        brand = self.kwargs.get('brandname')
        series = self.kwargs.get('seriesname')

        if series:
            queryset = Product.objects.filter(category__iexact=cat, brand__name__iexact = brand, series__iexact = series)
        
        return queryset

class CommentView(APIView):
    def post(self, request, product_id):
        data = request.data
        product = Product.objects.get(pk=product_id)
        user = request.user  # Get the user making the request
        serializer = CommentSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save(product=product, user = user)  
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReplyView(APIView):
    def post(self, request, comment_id):
        data = request.data
        comment = Comment.objects.get(pk=comment_id)
        user = request.user  # Get the user making the request
        serializer = ReplySerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save(comment=comment, user=user)  # Save the new comment
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RatingView(APIView):
    def post(self,request,product_id):
        data = request.data
        user = request.user
        product = Product.objects.get(pk=product_id)
        serializer = RatingSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(user=user, product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
            

class NavSearchView(APIView):   
    def get(self,request):
        search = request.query_params.get('search')
        #now get 10 products that match the search
        products = Product.objects.filter(name__icontains=search)[:10]
        list = []
        for p in products:
            list.append({"name":p.name,"id":p.product_id,"image":p.images.first().image.url, "price":p.price})
        return Response(list)

class NavCatView(APIView):
    def get(self,request):
        search = request.query_params.get('search')
        #now get brands and series that match the search
        #filter the products that match the search and then get brands and series that match the search
        products = Product.objects.filter(category__name__iexact=search)
        list = []
        brands = []
        for p in products:
            brand = p.brand.name
            series = p.brand.series.all()
            series = series.filter(category__name__iexact=search)
            series = SeriesSerializer(series,many=True).data
            if brand not in brands:
                brands.append(brand)
                list.append({"brand":brand,"series":series})
        return Response(list)


class EmiView(APIView):
    # permission_classes = [IsAuthenticated]
    def post(self,request):
        data = request.data
        serializer = EmiSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)   