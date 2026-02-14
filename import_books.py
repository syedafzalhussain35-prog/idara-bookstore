import os
import django
import csv

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'idara_project.settings')
django.setup()

from store.models import Book

def import_data():
    csv_file = 'books.csv' # Make sure your file is named this!
    
    print("Starting Book Import...")
    
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            # 1. Get the data from CSV columns
            title = row['Book Title'].strip()
            author = row['Author'].strip()
            price = (row.get('Price') or '').strip()
            
            # Combine Category and Subject for description
            category = row['Category'] if row['Category'] else ""
            subject = row['Subject'] if row['Subject'] else ""
            description = f"Category: {category}\nSubject: {subject}"
            
            # 2. Create the Book in Database
            # usage of get_or_create prevents duplicates if you run it twice
            book, created = Book.objects.get_or_create(
                title=title,
                defaults={
                    'author': author,
                    'price': price,
                    'description': description,
                    'stock': 50  # Default stock
                }
            )
            
            if created:
                count += 1
                print(f"Added: {title}")
            else:
                print(f"Skipped (Already exists): {title}")

    print(f"\nSuccessfully added {count} new books!")

if __name__ == '__main__':
    import_data()



    python import_books.py
