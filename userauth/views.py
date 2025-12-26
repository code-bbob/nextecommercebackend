from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .serializers import  UserLoginSerializer, UserRegistrationSerializer, UserPasswordResetSerializer, UserChangePasswordSerializer,SendPasswordResetEmailSerializer, UserInfoSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.core.files.base import ContentFile
import random
from .utils import Util
from .models import User
from .models import Otp
def generate_otp():
  random_number = random.randint(100000, 999999)
  return random_number

# Generate Token Manually
def get_tokens_for_user(user):

  refresh = RefreshToken.for_user(user)
  return {
      'refresh': str(refresh),
      'access': str(refresh.access_token),
  }


class SignupView(APIView):
  def post(self, request, format=None):
    request.data['email'] = request.data['email'].lower()
    otp = str(generate_otp())
    email = request.data['email'].lower()
    Otp.objects.create(otp=otp, email=email)
    print(otp)
    # request.session['otp'] = otp
    data = {
        'subject':'OTP for registration',
        'body': "Your otp is "+otp,
        'to_email':email
      } 
    Util.send_email(data)
    return Response({'msg':'sent otp'}, status=status.HTTP_200_OK)
  
class UserRegistrationView(APIView):
  def post(self,request, format=None):
    request.data['email'] = request.data['email'].lower()
    otpobtained=request.data['otp']
    stored_otp = Otp.objects.get(email=request.data['email']).otp
    print(stored_otp)
    if stored_otp:
      if otpobtained ==stored_otp:
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = get_tokens_for_user(user)
        object = Otp.objects.get(email=request.data['email'].lower())
        object.delete()
        return Response({'token':token, 'msg':'Registration Successful'}, status=status.HTTP_201_CREATED)
      else:
        return Response({'msg': 'Otp doesnt match try again!'}, status=status.HTTP_400_BAD_REQUEST)
    else:
      return Response({'msg': 'Otp is not present in the system!'}, status=status.HTTP_400_BAD_REQUEST)
    
# class UserLoginView(APIView):
#   def post(self, request, format=None):
#     request.data['email'] = request.data['email'].lower()
#     serializer = UserLoginSerializer(data=request.data)
#     serializer.is_valid(raise_exception=True)
#     email = serializer.data.get('email').lower()
#     password = serializer.data.get('password')
#     user = authenticate(email=email, password=password)
#     if user is not None:
#       token = get_tokens_for_user(user)
#       return Response({'token':token, 'msg':'Login Success'}, status=status.HTTP_200_OK)
#     else:
#       return Response({'errors':{'non_field_errors':['Email or Password is not Valid']}},status=status.HTTP_400_BAD_REQUEST)
    

class UserLoginView(APIView):
  def post(self, request, format=None):
    request.data['email'] = request.data['email'].lower()
    serializer = UserLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.data.get('email').lower()
    password = serializer.data.get('password')
    user = authenticate(email=email, password=password)
    if user is not None:
      token = get_tokens_for_user(user)
      user_serializer = UserInfoSerializer(user)
      return Response({
        'auth_token': str(token),
        'user': user_serializer.data,
        'msg': 'Login Success'
      }, status=status.HTTP_200_OK)
    else:
      return Response({'errors':{'non_field_errors':['Email or Password is not Valid']}},status=status.HTTP_400_BAD_REQUEST)

class UserChangePasswordView(APIView):
  permission_classes = [IsAuthenticated]
  def post(self, request, format=None):
    # Manually define or retrieve the user
    user = request.user  
    if not user:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check if the old password is provided in the request
    old_password = request.data.get('oldpassword', None)
    if not old_password:
        return Response({'error': 'Old password is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the provided old password matches the actual password of the user
    if not user.check_password(old_password):
        return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)

    # Continue with changing the password if the old password is correct
    serializer = UserChangePasswordSerializer(data=request.data, context={'user': user})
    serializer.is_valid(raise_exception=True)
    return Response({'msg': 'Password Changed Successfully'}, status=status.HTTP_200_OK)
  
  
class SendPasswordResetEmailView(APIView):
  def post(self, request, format=None):
    serializer = SendPasswordResetEmailSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response({'msg':'Password Reset link send. Please check your Email'}, status=status.HTTP_200_OK)

class UserPasswordResetView(APIView):
  def post(self, request, uid, token, format=None):
    serializer = UserPasswordResetSerializer(data=request.data, context={'uid':uid, 'token':token})
    serializer.is_valid(raise_exception=True)
    return Response({'msg':'Password Reset Successfully'}, status=status.HTTP_200_OK)

class UserInfoView(APIView):
  permission_classes = [IsAuthenticated]
  def get(self,request,*args, **kwargs):
    user=request.user
    id = self.kwargs.get('id')
    if id:
      user = User.objects.filter(id=id).first()
      user_serializer=UserInfoSerializer(user)
      userinfo = user_serializer.data
      return Response({"userinfo":userinfo}, status=status.HTTP_200_OK)
    else:
      user_serializer=UserInfoSerializer(user)
      userinfo = user_serializer.data
      return Response(userinfo, status=status.HTTP_200_OK)

  
  def patch(self,request):
    user = request.user
    new_bio = request.data.get("bio")
    serializer = UserInfoSerializer
    if new_bio:
      user.bio = new_bio
      user.save()
      return Response({"msg":"Bio Updated"}, status=status.HTTP_200_OK)
    else:
      return Response("msg: Something went wrong!", status=status.HTTP_400_BAD_REQUEST)
    




from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from .models import User  # Import your User model
from rest_framework_simplejwt.tokens import RefreshToken # For JWT
from django.http import HttpResponseRedirect
from django.db.models import Q

class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        redirect_uri = f"{settings.BASE_URL}/api/auth/google/callback/" # Important!
        authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={redirect_uri}&scope=openid profile email"
        return Response({"authorization_url": authorization_url})
    




class GoogleCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return Response({"error": "Missing authorization code"}, status=400)

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": f"{settings.BASE_URL}/api/auth/google/callback/", # Must match the one in Google Console
            "grant_type": "authorization_code"
        }
        response = requests.post(token_url, data=data).json()
        
        if 'id_token' not in response:
            return Response({'error': 'Failed to obtain ID token'}, status=400)

        try:
            idinfo = id_token.verify_oauth2_token(response['id_token'], google_requests.Request(), settings.GOOGLE_CLIENT_ID)

            email = idinfo.get('email')
            name = idinfo.get('name')
            google_id = idinfo.get('sub')
            picture_url = idinfo.get('picture')

            
            

            # user, created = User.objects.get_or_create(google_id=google_id, email = email,defaults={'email': email, 'name': name})

            try:
              # 1. Try to find an existing user by google_id OR email
              user = User.objects.get(Q(google_id=google_id) | Q(email=email))

              # 2. If the user was found with a different google_id, update it
              if user.google_id!= google_id:
                  user.google_id = google_id
                  user.save()

            except User.DoesNotExist:
                # 3. If no user is found, create a new one
                user = User.objects.create(google_id=google_id, email=email, name=name)
                if picture_url:
                  try:
                      response = requests.get(picture_url, stream=True)
                      response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

                      file_name = f"{google_id}.jpg"  # Or .png, depending on the image type

                      user.dp.save(file_name, ContentFile(response.content), save=True)
                  except requests.exceptions.RequestException as e:
                      print(f"Error downloading profile picture: {e}")
                  except Exception as e:
                      print(f"Error saving profile picture: {e}")

            # JWT Token Generation (Uncommented and Corrected):
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token  # Access token is obtained from the refresh token

            redirect_url = f"{settings.FRONTEND_URL}auth/callback?access={access}&refresh={refresh}"
            return HttpResponseRedirect(redirect_url)

            # return Response({"access": str(access), "refresh": str(refresh)})

        except ValueError as e:  # Catch specific ValueError and print the error
            print(f"Token verification error: {e}") # Debugging
            return Response({'error': 'Invalid token'}, status=400)

        except Exception as e: # Catch any other exceptions
            print(f"An unexpected error occurred: {e}") # Debugging
            return Response({'error': 'An unexpected error occurred'}, status=500) # Generic error message