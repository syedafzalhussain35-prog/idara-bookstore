from django.shortcuts import render, get_object_or_404, redirect
from .models import Book, Cart, CartItem, Order, OrderItem, Wishlist, Category
from .forms import CheckoutForm
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q 

# Email specific imports for HTML content
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# 1. Homepage (Updated for Categories)
def home(request):
    category_slug = request.GET.get('category') # Get ?category=... from URL
    query = request.GET.get('q') 

    books = Book.objects.all()

    # Filter by Category if clicked
    if category_slug:
        books = books.filter(category__slug=category_slug)

    # Filter by Search if typed
    if query:
        books = books.filter(
            Q(title__icontains=query) | 
            Q(author__icontains=query) |
            Q(description__icontains=query)
        )
    
    return render(request, 'store/home.html', {'books': books, 'query': query})

# 2. Book Detail
def book_detail(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    return render(request, 'store/book_detail.html', {'book': book})

# 3. Signup
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'store/signup.html', {'form': form})

# 4. Login
def login_page(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'store/login.html', {'form': form})

# --- WISHLIST LOGIC ---

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def add_to_wishlist(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    Wishlist.objects.get_or_create(user=request.user, book=book)
    return redirect('wishlist')

@login_required
def remove_from_wishlist(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    Wishlist.objects.filter(user=request.user, book=book).delete()
    return redirect('wishlist')

# --- PROFILE LOGIC ---

@login_required
def profile_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/profile.html', {'orders': orders})

# --- CART LOGIC ---

@login_required
def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
        
    return redirect('cart_detail')

@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart.html', {'cart': cart})

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    if cart_item.cart.user == request.user:
        cart_item.delete()
    return redirect('cart_detail')

# --- CHECKOUT LOGIC (With Branded HTML Email) ---

@login_required
def checkout(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # 1. Save Order
            order = form.save(commit=False)
            order.user = request.user
            order.total_cost = sum(item.total_price for item in cart.items.all())
            order.save()
            
            # 2. Save Items
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    book=item.book,
                    price=item.book.price,
                    quantity=item.quantity
                )
            
            # 3. Send Branded HTML Email Receipt
            subject = f'Order Confirmation - Idara Kitab Ul Shifa (# {order.id})'
            from_email = 'idara.kitabulshifa@gmail.com'
            to = [request.user.email]

            # Rendering the HTML template with order details
            html_content = render_to_string('emails/order_confirmation.html', {'order': order})
            text_content = strip_tags(html_content) # Fallback for plain-text clients

            # Constructing the email with alternative HTML content
            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=True)

            # 4. Clear Cart
            cart.items.all().delete()
            return render(request, 'store/order_success.html', {'order': order})
            
    else:
        form = CheckoutForm()
        
    return render(request, 'store/checkout.html', {'form': form, 'cart': cart})

# 5. Contact View
def contact_view(request):
    return render(request, 'store/contact.html')