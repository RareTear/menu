from rest_framework import viewsets, permissions, generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Product, Category, CartItem, Restaurant
from .serializers import (
    ProductSerializer, CategorySerializer, CartItemSerializer, UserSerializer,
    CartItemAddSerializer, RestaurantSerializer)
from django.contrib.auth.models import User
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import filters


class CategoryView(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [
        permissions.IsAdminUser, permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class ProductView(viewsets.ModelViewSet):
    queryset = Product.available.all()
    serializer_class = ProductSerializer
    permission_classes = [
        permissions.IsAdminUser, permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description', 'category__name']


class UserView(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class CartItemView(generics.ListAPIView):
    serializer_class = CartItemSerializer
    permission_classes = (permissions.IsAuthenticated, )
    filter_backends = [filters.SearchFilter]
    search_fields = [
        'product__name', 'product__description', 'product__category__name']

    def get_queryset(self):
        user = self.request.user
        return CartItem.objects.filter(user=user)


class CartItemAddView(generics.CreateAPIView):
    queryset = CartItem.objects.all()
    serializer_class = CartItemAddSerializer
    permission_classes = (permissions.IsAuthenticated, )


class CartItemDelView(generics.DestroyAPIView):
    permission_classes = (permissions.IsAuthenticated, )
    queryset = CartItem.objects.all()

    def delete(self, request, pk, format=None):
        user = request.user
        cart_item = CartItem.objects.filter(user=user)
        target_product = get_object_or_404(cart_item, pk=pk)
        product = get_object_or_404(Product, id=target_product.product.id)
        product.quantity = product.quantity + target_product.quantity
        product.save()
        target_product.delete()
        return Response(status=status.HTTP_200_OK, data={"detail": "deleted"})


class CartItemAddOneView(APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def get(self, request, pk, format=None):
        user = request.user
        cart_item = CartItem.objects.filter(user=user)
        target_product = cart_item.get(pk=pk)
        product = get_object_or_404(Product, id=target_product.product.id)
        if product.quantity <= 0:
            return Response(
                data={
                    "detail": "this item is sold out try another one !",
                    "code": "sold_out"})

        target_product.quantity = target_product.quantity + 1
        product.quantity = product.quantity - 1
        product.save()
        target_product.save()
        return Response(
            status=status.HTTP_226_IM_USED,
            data={"detail": 'one object added', "code": "done"})


class CartItemReduceOneView(APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def get(self, request, pk, format=None):
        user = request.user
        cart_item = CartItem.objects.filter(user=user)
        target_product = cart_item.get(pk=pk)
        product = get_object_or_404(Product, id=target_product.product.id)
        if target_product.quantity == 0:
            return Response(
                data={
                    "detail": "there is no more item like this in tour cart",
                    "code": "no_more"})

        target_product.quantity = target_product.quantity - 1
        product.quantity = product.quantity + 1
        product.save()
        target_product.save()
        return Response(
            status=status.HTTP_226_IM_USED,
            data={
                "detail": 'one object deleted',
                "code": "done"
            })

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all().prefetch_related(
        'categories', 'categories__foods')
    serializer_class = RestaurantSerializer

    def list(self, request):

        if request.query_params == {}:
            queryset = Restaurant.objects.all()
        else:
            query = request.query_params['search']
            queryset = Restaurant.objects.filter(name__icontains=query)

        serializer = RestaurantSerializer(
            queryset, many=True, fields=('id', 'name', 'address',))
        return Response(serializer.data)

    def create(self, request):
        if not request.user.is_restaurant:
            return Response({'message': 'unauthorized'}, 401)

        serializer = RestaurantSerializer(
            data=request.data, fields=('id', 'name', 'address',))

        if not serializer.is_valid():
            return Response(serializer.errors)

        serializer.save(user=request.user)

        return Response(serializer.data)

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]