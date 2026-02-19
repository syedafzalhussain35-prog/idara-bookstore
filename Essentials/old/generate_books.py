import pandas as pd

# Load Excel File
df = pd.read_excel("data/books_data.xlsx")

# Group books by subject
grouped_books = df.groupby("Subject")

# Start HTML Structure
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NCISM Books</title>
    <link rel="stylesheet" href="styles.css"> <!-- Make sure styles.css exists -->
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h3>Explore Subject-wise</h3>
            <ul>
"""

# Generate Sidebar Links
subjects = df["Subject"].unique()
for subject in subjects:
    html_content += f'                <li><a href="#{subject.lower().replace(" ", "-")}">{subject}</a></li>\n'

html_content += """
            </ul>
        </div>
        <div class="content">
            <h1>NCISM 1st Prof Books</h1>
"""

# Generate Book Cards for Each Subject
for subject, books in grouped_books:
    subject_id = subject.lower().replace(" ", "-")  # Convert to lowercase with hyphens for ID
    html_content += f'            <h2 id="{subject_id}">{subject}</h2>\n'
    
    for _, book in books.iterrows():
        html_content += f"""
            <div class="book-card">
                <div class="image-slider">
                    <button class="prev">❮</button>
                    <img src="{book['Image 1']}" class="active" alt="Book Image 1">
                    <img src="{book['Image 2']}" alt="Book Image 2">
                    <img src="{book['Image 3']}" alt="Book Image 3">
                    <button class="next">❯</button>
                </div>
                <h3>{book['Book Title']}</h3>
                <p class="author"><strong>Author:</strong> {book['Author']}</p>
                <p><strong>Binding:</strong> {book['Binding']}</p>
                <p><strong>Pages:</strong> {book['Pages']}</p>
                <p><strong>Edition:</strong> {book['Edition']}</p>
                <p><strong>MRP:</strong> {book['MRP']}</p>
                <p class="discount-price">Offer Price: {book['Offer Price']}</p>
                <div class="buy-section">
                    <p>Buy from:</p>
                    <div class="buy-options">
                        <a href="{book['WhatsApp Link']}" target="_blank"><img src="icons/whatsappp.PNG" alt="Buy on WhatsApp"></a>
                        <a href="{book['Amazon Link']}" target="_blank"><img src="icons/amazon.png" alt="Buy on Amazon"></a>
                        <a href="{book['Flipkart Link']}" target="_blank"><img src="icons/flipkart.png" alt="Buy on Flipkart"></a>
                        <a href="{book['Meesho Link']}" target="_blank"><img src="icons/meesho.png" alt="Buy on Meesho"></a>
                    </div>
                </div>
            </div>
        """

html_content += """
        </div>
    </div>
</body>
</html>
"""

# Save to an HTML File (Changed to "data.html")
with open("data.html", "w", encoding="utf-8") as file:
    file.write(html_content)

print("✅ HTML file generated successfully: data.html")
