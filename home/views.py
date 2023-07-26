from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from django.shortcuts import render, HttpResponse, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from graphical_pwd_auth.settings import N, TBA, EMAIL_HOST_USER, ALLOWED_HOSTS
from .models import LoginInfo
import random, uuid


def get_pwd_imgs():
    # These images are just to confuse the attacker
    images = random.sample(range(1, 39), N * N)
    print(images)
    p_images = []
    for i in range(0, N * N, N):
        p_images.append(images[i:i+N])
    print(p_images)
    return p_images
    

def update_login_info(user, didSuccess):
    if didSuccess:
        user.logininfo.fails = 0
    else:
        user.logininfo.fails += 1
    
    user.logininfo.save()
    print('{} Failed attempts: {}'.format(user.username, user.logininfo.fails))


def isBlocked(username):
    try:
        user = User.objects.get(username=username)
    except Exception:
        return None
    print('isBlocked: {} - {}'.format(user.logininfo, TBA))
    if user.logininfo.fails >= TBA:
        return True
    else:
        return False


def sendLoginLinkMailToUser(username):
    user = User.objects.get(username=username)
    # send email only id user.logininfo.login_link is not None
    if user.logininfo.login_link is None:
        link = str(uuid.uuid4())
        user.logininfo.login_link = link
        user.logininfo.save()
        email = EmailMessage(
            subject='Link to Log in to your account',
            body='''
            Someone tried to bruteforce on your account.
            Click the Link to Login to your account directly.
            The link is one-time clickable
            link: http://{}:8000/login/{}
            '''.format(ALLOWED_HOSTS[-1], link), # might wanna change the allowd_host
            from_email=EMAIL_HOST_USER,
            to=[user.email],
        )
        email.send()
        print('LOGIN LINK EMAIL SENT')


def sendPasswordResetLinkToUser(username):
    # send reset link everytime user requests
    try:
        user = User.objects.get(username=username)
    except Exception:
        return False
    
    link = str(uuid.uuid4())
    user.logininfo.reset_link = link
    user.logininfo.save()
    
    email_msg = '''
        You have requested to reset your password.
        Click the Link to reset your password directly.
        The link is one-time clickable
        link: http://{}:8000/reset/{}
        '''.format(ALLOWED_HOSTS[-1], link)
    print(email_msg)
    send_mail(user.email,email_msg)
    print('PWD RESET LINK EMAIL SENT')
    return True


def home_page(request):
    return render(request, 'home.html')


def register_page(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        print(username, password)
        try:
            # create user and loginInfo for him
            user = User.objects.create_user(email=email, username=username, password=password)
            login_info = LoginInfo(user=user, fails=0)
            login_info.save()
            messages.success(request, 'Account created successfully!')
        except Exception:
            messages.warning(request, 'Error while creating Account!')
        
        return redirect('home')
    else:
        data = {
            'p_images': get_pwd_imgs(),
        }
        return render(request, 'register.html', context=data)


def login_page(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        print(username, password)

        block_status = isBlocked(username)
        if block_status is None:
            # No user exists
            messages.warning(request, 'Account doesn\'t Exist')
            return redirect('login')

        elif block_status == True:
            # Blocked - send login link to email
            # check if previously sent, if not send
            sendLoginLinkMailToUser(username)
            messages.warning(request, 'Your account is Blocked, please check your Email!')
            return redirect('login')
        else:
            # Not Blocked
            user = authenticate(username=username, password=password, request=request)
            if user is not None:
                login(request, user)
                update_login_info(user, True)
                messages.success(request, 'Login successfull!')
                return redirect('home')
            else:
                user = User.objects.get(username=username)
                update_login_info(user, False)
                messages.warning(request, 'Login Failed!')
                return redirect('login')

    else:
        data = {
            'p_images': get_pwd_imgs(),
        }
        return render(request, 'login.html', context=data)


def login_from_uid(request, uid):
    try:
        # get user from the uid and reset the Link to 'NO_LINK' again
        login_info = LoginInfo.objects.get(login_link=uid)
        user = login_info.user
        login(request, user)
        update_login_info(user, True)
        login_info.login_link = None
        login_info.save()
        messages.success(request, 'Login successfull!')
    except Exception:
        messages.warning(request, 'Invalid Link. Please check again!')

    return redirect('home')


def reset_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        print(username)
        if sendPasswordResetLinkToUser(username):
            messages.success(request, 'Password Reset Link sent to you email!')
        else:
            messages.warning(request, 'User doesn\'t exist!')
        return redirect('home')
    else:
        return render(request, 'reset_request.html')


def reset_from_uid(request, uid):
    print('hello')
    if request.method == 'POST':
        print('hi-post')
        password = request.POST['password']
        try:
            # get user from the uid and reset the Link to 'NO_LINK' again
            login_info = LoginInfo.objects.get(reset_link=uid)
            user = login_info.user
            # reset pwd
            user.set_password(password)
            login_info.reset_link = None
            login_info.save()
            user.save()
            messages.success(request, 'Password Changed Successfully!')
        except Exception:
            messages.warning(request, 'Invalid Link. Please check again!')
        return redirect('home')
    else:
        print('hi-else')
        try:
            # To make sure the link is valid
            print(uid)
            login_info = LoginInfo.objects.get(reset_link=uid)
            data = {
                'p_images': get_pwd_imgs(),
            }
            return render(request, 'reset.html', context=data)
        except Exception:
            messages.warning(request, 'Invalid Link. Please check again!')
            return redirect('home')


def logout_page(request):
    logout(request)
    messages.warning(request, 'You\'ve been logged out!')
    return redirect('home')



def send_mail(id,msg):
    print(id)
    from_id='redrondoofdeath@gmail.com'
    conn =smtplib.SMTP('smtp.gmail.com',587)  
    type(conn)  
    conn.ehlo()  
    conn.starttls()  
    message = MIMEMultipart("alternative")
    message["Subject"] = "Link to reset your password"
    message["From"] = from_id
    message["To"] = id
    text=msg
    msg = MIMEText(text, "plain")
    message.attach(msg)

 
    conn.login(from_id,'qweqanqiodlxvpec')  
    conn.sendmail(from_id,id,message.as_string())  
    conn.quit() 




















# from django.shortcuts import render, HttpResponse, redirect
# from django.contrib import messages
# from django.contrib.auth import authenticate, logout, login
# from django.contrib.auth.models import User
# from django.core.mail import EmailMessage, send_mail
# from graphical_pwd_auth.settings import N, TBA, EMAIL_HOST_USER, ALLOWED_HOSTS
# from .models import LoginInfo
# import random, uuid


# def get_pwd_imgs():
#     # These images are just to confuse the attacker
#     images = random.sample(range(1, 39), N * N)
#     print(images)
#     p_images = []
#     for i in range(0, N * N, N):
#         p_images.append(images[i:i+N])
#     print(p_images)
#     return p_images
    

# def update_login_info(user, didSuccess):
#     if didSuccess:
#         user.logininfo.fails = 0
#     else:
#         user.logininfo.fails += 1
    
#     user.logininfo.save()
#     print('{} Failed attempts: {}'.format(user.username, user.logininfo.fails))


# def isBlocked(username):
#     try:
#         user = User.objects.get(username=username)
#     except Exception:
#         return None
#     print('isBlocked: {} - {}'.format(user.logininfo, TBA))
#     if user.logininfo.fails >= TBA:
#         return True
#     else:
#         return False


# def sendLoginLinkMailToUser(username):
#     user = User.objects.get(username=username)
#     # send email only id user.logininfo.login_link is not None
#     if user.logininfo.login_link is None:
#         link = str(uuid.uuid4())
#         user.logininfo.login_link = link
#         user.logininfo.save()
#         send_mail(user.id,'''Someone tried to bruteforce on your account.\nClick the Link to Login to your account directly.\nThe link is one-time clickable\nlink: http://{}:8000/login/{}'''.format(ALLOWED_HOSTS[-1], link),
#             EMAIL_HOST_USER,[user.email],
#             fail_silently=False,

#             )
#         #email = EmailMessage(
#          #   subject='Link to Log in to your account',
#           #  body='''
#            # Someone tried to bruteforce on your account.
#             #Click the Link to Login to your account directly.
#             #he link is one-time clickable
#             #link: http://{}:8000/login/{}'''.format(ALLOWED_HOSTS[-1], link), # might wanna change the allowd_host
#             #from_email=EMAIL_HOST_USER,
#             #to=[user.email],
#         #)
#         #email.send()
#         print('LOGIN LINK EMAIL SENT')


# def sendPasswordResetLinkToUser(username):
#     # send reset link everytime user requests
#     try:
#         user = User.objects.get(username=username)
#     except Exception:
#         return False
    
#     link = str(uuid.uuid4())
#     user.logininfo.reset_link = link
#     user.logininfo.save()
#     #print(user.email)
#     #email = EmailMessage(
#      #   subject='Link to Rest your Password',
#       #  body='''
#        # You have requested to reset your password.
#         #Click the Link to reset your password directly.
#         #he link is one-time clickable
#         #link: http://{}:8000/reset/{}
#         #'''.format(ALLOWED_HOSTS[-1], link), # might wanna change the allowd_host
#         #from_email=EMAIL_HOST_USER,
#         #to=[user.email],
#     #)

#     print(type(user.email))
#     send_mail(user.email, '''Someone tried to bruteforce on your account.\nClick the Link to Login to your account directly.\nThe link is one-time clickable\nlink: http://{}:8000/login/{}'''.format(ALLOWED_HOSTS[-1], link))

#      #send_mail('Link to Log in to your account','''
#     #         Someone tried to bruteforce on your account.
#     #         Click the Link to Login to your account directly.
#     #         The link is one-time clickable
#     #         link: http://{}:8000/login/{}'''.format(ALLOWED_HOSTS[-1], link),
#     #         EMAIL_HOST_USER,[user.email],
#     #         fail_silently=False,
#     #       )
#     #email.send()
#     print('PWD RESET LINK EMAIL SENT')
#     return True


# def home_page(request):
#     return render(request, 'home.html')


# def register_page(request):
#     if request.method == 'POST':
#         username = request.POST['username']
#         email = request.POST['email']
#         password = request.POST['password']
#         print(username, password, email)
#         try:
#             # create user and loginInfo for him
#             user = User.objects.create_user(email=email, username=username, password=password)
#             login_info = LoginInfo(user=user, fails=0)
#             login_info.save()
#             messages.success(request, 'Account created successfully!')
#         except Exception:
#             messages.warning(request, 'Error while creating Account!')
        
#         return redirect('home')
#     else:
#         data = {
#             'p_images': get_pwd_imgs(),
#         }
#         return render(request, 'register.html', context=data)


# def login_page(request):
#     if request.method == 'POST':
#         username = request.POST['username']
#         password = request.POST['password']
#         print(username, password)

#         block_status = isBlocked(username)
#         if block_status is None:
#             # No user exists
#             messages.warning(request, 'Account doesn\'t Exist')
#             return redirect('login')

#         elif block_status == True:
#             # Blocked - send login link to email
#             # check if previously sent, if not send
#             sendLoginLinkMailToUser(username)
#             messages.warning(request, 'Your account is Blocked, please check your Email!')
#             return redirect('login')
#         else:
#             # Not Blocked
#             user = authenticate(username=username, password=password, request=request)
#             if user is not None:
#                 login(request, user)
#                 update_login_info(user, True)
#                 messages.success(request, 'Login successfull!')
#                 return redirect('home')
#             else:
#                 user = User.objects.get(username=username)
#                 update_login_info(user, False)
#                 messages.warning(request, 'Login Failed!')
#                 return redirect('login')

#     else:
#         data = {
#             'p_images': get_pwd_imgs(),
#         }
#         return render(request, 'login.html', context=data)


# def login_from_uid(request, uid):
#     try:
#         # get user from the uid and reset the Link to 'NO_LINK' again
#         login_info = LoginInfo.objects.get(login_link=uid)
#         user = login_info.user
#         login(request, user)
#         update_login_info(user, True)
#         login_info.login_link = None
#         login_info.save()
#         messages.success(request, 'Login successfull!')
#     except Exception:
#         messages.warning(request, 'Invalid Link. Please check again!')

#     return redirect('home')


# def reset_view(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         print(username)
#         if sendPasswordResetLinkToUser(username):
#             messages.success(request, 'Password Reset Link sent to you email!')
#         else:
#             messages.warning(request, 'User doesn\'t exist!')
#         return redirect('home')
#     else:
#         return render(request, 'reset_request.html')


# # def smtp_reset_view(receiver):
# #     s = smtplib.SMTP('smtp.mail.yahoo.com', 587)
# #     s.starttls()
# #     s.ehlo()        
# #     s.login("devanshukhemka040@yahoo.com", r"@lchem1stMe")

# #     message = "hello world message"

# #     s.sendmail("devanshukhemka040@yahoo.com", receiver, message)

# # # !!!!!!!!!!    I QUIT        !!!!!!!!!!!!!!!!!!
# # # 
# # #   s.quit()






# def reset_from_uid(request, uid):
#     print('hello')
#     if request.method == 'POST':
#         print('hi-post')
#         password = request.POST['password']
#         try:
#             # get user from the uid and reset the Link to 'NO_LINK' again
#             login_info = LoginInfo.objects.get(reset_link=uid)
#             user = login_info.user
#             # reset pwd
#             user.set_password(password)
#             login_info.reset_link = None
#             login_info.save()
#             user.save()
#             messages.success(request, 'Password Changed Successfully!')
#         except Exception:
#             messages.warning(request, 'Invalid Link. Please check again!')
#         return redirect('home')
#     else:
#         print('hi-else')
#         try:
#             # To make sure the link is valid
#             print(uid)
#             login_info = LoginInfo.objects.get(reset_link=uid)
#             data = {
#                 'p_images': get_pwd_imgs(),
#             }
#             return render(request, 'reset.html', context=data)
#         except Exception:
#             messages.warning(request, 'Invalid Link. Please check again!')
#             return redirect('home')


# def logout_page(request):
#     logout(request)
#     messages.warning(request, 'You\'ve been logged out!')
#     return redirect('home')




