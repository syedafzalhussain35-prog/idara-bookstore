from django.shortcuts import render, get_object_or_404, redirect
from .models import Book, Cart, CartItem, Order, OrderItem
from .forms import CheckoutForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q  # Essential for the search bar

# 1. Homepage (With Search Logic)
def home(request):
    query = request.GET.get('q') # Get the search term
    
    if query:
        # Search in Title, Author, or Description
        books = Book.objects.filter(
            Q(title__icontains=query) | 
            Q(author__icontains=query) |
            Q(description__icontains=query)
        )
    else:
        # No search? Show all books
        books = Book.objects.all()
        
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

# 4. Add to Cart
@login_required
def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, book=book)
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
        
    return redirect('cart_detail')

# 5. View Cart
@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart.html', {'cart': cart})

# 6. Checkout
@login_required
def checkout(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.total_cost = sum(item.total_price for item in cart.items.all())
            order.save()
            
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    book=item.book,
                    price=item.book.price,
                    quantity=item.quantity
                )
            
            cart.items.all().delete()
            return render(request, 'store/order_success.html', {'order': order})
            
    else:
        form = CheckoutForm()
        
    return render(request, 'store/checkout.html', {'form': form, 'cart': cart})