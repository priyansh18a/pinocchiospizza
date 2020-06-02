
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, MultipleObjectsReturned
from django.shortcuts import render, redirect, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template.loader import render_to_string
from .models import PizzaTopping, SubExtra, MenuItem, OrderItem, Order
from .view_2 import model_dict, cart, cart_count, update_total
from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags



# Create your views here.
def register_view(request):
    if request.method == 'GET':
        return render(request, 'orders/register.html', {'message': None})
    else:
        username = request.POST['username']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is None:
            new_user = User.objects.create_user(username, email, password,
                                                first_name=first_name,
                                                last_name=last_name)
            new_user.save()
            login(request, new_user)
            return HttpResponseRedirect(reverse('index'))
        else:
            return render(request,
                          'orders/register.html',
                          {'message': 'User already exists.'})

def index(request):
    if not request.user.is_authenticated:
        return render(request, 'orders/login.html', {'form':  AuthenticationForm,'message': None})

    return HttpResponseRedirect(reverse('menu'))


class LoginView(View):
    def get(self, request):
        return render(request, 'orders/login.html', { 'form':  AuthenticationForm,'message': None})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            try:
                form.clean()
            except ValidationError:
                return render(
                    request,
                    'survey/login.html',
                    { 'form': form, 'invalid_creds': True }
                )

            login(request, form.get_user())

            return redirect(reverse('profile'))

        return render(request, 'orders/login.html', { 'form': form,'message': 'Invalid Credential' })

login_required(redirect_field_name='index')
def ProfileView(request):
    context = {
            "user": request.user
        }
    return render(request, 'orders/profile.html',context)

login_required(redirect_field_name='index')
def menu_view(request):
    # Order menu page. Convert model objects to dicts for format reasons.
    context = {
        'message': None,
        'regular': model_dict(MenuItem, 'Regular Pizza'),
        'sicilian': model_dict(MenuItem, 'Sicilian Pizza'),
        'toppings': PizzaTopping.objects.all(),
        'subs': model_dict(MenuItem, 'Subs'),
        'extras': model_dict(SubExtra),
        'pasta': model_dict(MenuItem, 'Pasta'),
        'salads': model_dict(MenuItem, 'Salads'),
        'platters': model_dict(MenuItem, 'Dinner Platters'),
        'cartcount': cart_count(request.user)
    }
    return render(request, 'orders/menu.html', context)

@login_required(redirect_field_name='index')
def cart_view(request):
    """
        View items in one's cart.
    """
    customer = request.user
    order = cart(customer)
    context = {
        'message': None,
        'order': order,
        'cart': order.items.all(),
        'cartcount': cart_count(customer),
        'total': order.total
    }
    return render(request, 'orders/cart.html', context)

login_required(redirect_field_name='index')
def pending_view(request):
    """
        View orders placed but not yet marked completed.
    """
    username = request.user
    customer = User.objects.get(username=username)
    orders = Order.objects.filter(
        placed=True, completed=False,
        in_cart=False, customer=customer
    )
    context = {
        'message': None,
        'orders': orders,
        'cartcount': cart_count(username)
    }
    return render(request, 'orders/pending.html', context)

@login_required(redirect_field_name='index')
def history_view(request):
    """
        View orders marked completed.
    """
    username = request.user
    customer = User.objects.get(username=username)
    orders = Order.objects.filter(completed=True, customer=customer)
    context = {
        'message': None,
        'orders': orders,
        'cartcount': cart_count(username)
    }
    return render(request, 'orders/history.html', context)

@login_required(redirect_field_name='index')
def empty_cart(request):
    """
        Empty one's cart.
    """
    username = request.user
    customer = User.objects.get(username=username)
    try:
        id = request.POST['orderid']
        Order.objects.get(id=int(id), customer=customer).delete()
    except ProtectedError:
        raise Http404('Failed to remove order object.')
    except Order.DoesNotExist:
        raise Http404('Order does not exist. Are you the customer?')

    return HttpResponseRedirect(reverse('cart'))

@login_required(redirect_field_name='index')
def additem(request):
    """
        Add orders to cart.
    """
    if request.method == 'POST':
        customer = request.user
        category = request.POST['category']
        kind = request.POST['kind']
        qty = int(request.POST['qty'])
        order = cart(customer)

        # Pasta, Salads
        if 'size' not in request.POST:

            # Get price and add item
            try:
                menuitem = MenuItem.objects.get(category=category, kind=kind)
            except MenuItem.DoesNotExist:
                raise Http404("Can't find price for added item.")
            else:
                for i in range(qty):
                    newitem = OrderItem(
                        category=category,
                        kind=kind,
                        price=menuitem.price,
                        order=order
                    )
                    newitem.save()
                    update_total(order)

        # Regular Pizza, Silician Pizza, Subs, Dinner Platters (have sizes)
        else:
            size = request.POST['size']

            try:
                menuitem = MenuItem.objects.get(
                category=category,
                kind=kind,
                size=size
            )
            except MenuItem.DoesNotExist:
                raise Http404("Can find price for added item.")
            else:
                for i in range(qty):
                    newitem = OrderItem(
                        category=category,
                        kind=kind,
                        price=menuitem.price,
                        size=size,
                        order=order
                    )
                    newitem.save()
                    update_total(order)
                    # Add toppings for pizzas
                    if 'Pizza' in category:
                        if ('topping' in kind or 'Special' in kind or
                                'item' in kind):
                            if 'Special' in kind:
                                toppingnum = 5
                            else:
                                toppingnum = int(kind[0])
                            for n in range(1, toppingnum+1):
                                toppingname=request.POST.get(
                                    'topping'+str(n),
                                    False
                                )
                                if toppingname:
                                    try:
                                        topping = PizzaTopping.objects.get(
                                            name=toppingname
                                        )
                                    except PizzaTopping.DoesNotExist:
                                        raise Http404("""
                                            Can't find that pizza topping.
                                        """)
                                    else:
                                        newitem.toppings.add(topping)
                                        newitem.save()

                    if 'Subs' in category:
                        # Extras (append to item and add to cart total)
                        for n in range(5):
                            extraname = request.POST.get('extra'+str(n), False)
                            if extraname:
                                try:
                                    itemextra = SubExtra.objects.get(
                                        name=extraname
                                    )
                                    menuextra = MenuItem.objects.get(
                                        category=category,
                                        kind=extraname,
                                        size=size
                                    )
                                except MenuItem.DoesNotExist:
                                    raise Http404("""
                                        Can't find subextra on menu.
                                    """)
                                except SubExtra.DoesNotExist:
                                    raise Http404("Can't find extra.")
                                else:
                                    newitem.extras.add(itemextra)
                                    newitem.save()

                                    newextra = OrderItem(
                                        category=menuextra.category,
                                        kind=menuextra.kind,
                                        size=menuextra.size,
                                        price=menuextra.price,
                                        order=order,
                                        extra=True
                                    )
                                    newextra.save()
                                    order.items.add(newextra)
                                    order.save()
                                    update_total(order)

    return HttpResponseRedirect(reverse('menu'))



@login_required(redirect_field_name='index')
def place(request):
    """
        Place an order.
    """
    customer = request.user
    user = User.objects.get(username=customer)
    try:
        cart = Order.objects.get(customer=customer, in_cart=True)
    except Order.MultipleObjectsReturned:
        raise Http404("More than one cart found.")
    except Order.DoesNotExist:
        raise Http404("No cart exists.")
    else:
        cart.placed = True
        cart.in_cart = False
        cart.save()
     #send_mail(subject,message,from_email ,to_list,fail_silently=False(To raise an error))

        # message='Your ORDER details are as follow'
        subject = 'Pinocchios Pizza & Subs Order Details'
        html_message = render_to_string('orders/order_email.html', {'name': customer,'order':cart})
        plain_message = strip_tags(html_message)
        from_email = settings.EMAIL_HOST_USER
        to = user.email
        mail.send_mail(subject, plain_message, from_email, [to], html_message=html_message)

    context = {
        'user': customer,
        'order': cart,
        'cartcount': cart_count(customer)
    }
    return render(request, 'orders/thanks.html', context)

"""check onces"""


@login_required(redirect_field_name='index')
def charge(request):
    """
        Charge order with Stripe.
    """
    customer = request.user
    order = cart(customer)
    context = {
        'message': None,
        'order': order,
        'cart': order.items.all(),
        'cartcount': cart_count(customer),
        'total': order.total,
        'paid': True
    }
    return render(request, 'orders/checkout.html', context)

    # Superuser-related views below.

@login_required(redirect_field_name='index')
def orders_view(request):
    """
        View placed orders from all customers. Superuser-use-only.
        Superuser can mark orders as completed or delete them.
    """
    if request.user.is_superuser:
        orders = Order.objects.filter(placed=True, completed=False)

        context = {
            'message': None,
            'orders': orders,
            'cartcount': cart_count(request.user)
        }
        return render(request, 'orders/orders.html', context)
    else:
        raise Http404("You are not authorized to view this page.")


@user_passes_test(lambda u: u.is_superuser)
def cancel_order(request):
    """
        Superuser cancels an order.
    """
    try:
        id = request.POST['orderid']
        Order.objects.get(id=int(id)).delete()
    except ProtectedError:
        raise Http404('Failed to remove order object.')
    except Order.DoesNotExist:
        raise Http404('Order does not exist.')

    return HttpResponseRedirect(reverse('orders'))


@user_passes_test(lambda u: u.is_superuser)
def complete_order(request):
    """
        Superuser marks an order as completed.
    """
    try:
        id = request.POST['orderid']
        order = Order.objects.get(id=int(id))
        order.in_cart=False
        order.placed=False
        order.completed=True
        order.save()
    except Order.DoesNotExist:
        raise Http404('Order does not exist.')

    return HttpResponseRedirect(reverse('orders'))
