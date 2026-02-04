from .models import Category

def navbar_categories(request):
    """
    Makes categories available globally in templates
    for navbar, footer, mega-menu, etc.
    """
    return {
        'nav_categories': (
            Category.objects
            .all()
            .order_by('name')
        )
    }
