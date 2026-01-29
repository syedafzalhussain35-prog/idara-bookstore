document.addEventListener('DOMContentLoaded', async () => {
    // --- Step 1: Define the Google Sheet URL ---
    const sheetURL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS3n4M-2hUV3y71_Cdpq0qT6Dn6D4d5IE5fsK4JXxNwumtvHSAthKPb9x9cP8_1AE9xHpZSeoR1k_du/pub?output=csv";

    // --- Step 2: Create variables to hold the data ---
    let books = {};       // An object for quick lookups by ID
    let booksArray = [];  // An array for easy looping and filtering

    // --- Step 3: Fetch and Parse Data from Google Sheets ---
    async function loadInventory() {
        try {
            const response = await fetch(sheetURL);
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            const csvText = await response.text();
            
            // Parse the CSV text into a usable format
            const lines = csvText.trim().split('\n');
            const headers = lines[0].split(',').map(h => h.trim());
            
            for (let i = 1; i < lines.length; i++) {
                const rowValues = lines[i].split(',');
                const bookData = {};
                headers.forEach((header, index) => {
                    // Handle potential commas within a value if your data is ever wrapped in quotes
                    bookData[header] = (rowValues[index] || "").trim();
                });

                if(bookData.id) { // Ensure the row has an ID
                    books[bookData.id] = bookData;
                    booksArray.push(bookData);
                }
            }
        } catch (error) {
            console.error("Failed to load inventory:", error);
            // Optionally, display an error message to the user on the page
            const bookContainer = document.getElementById("bookContainer");
            if(bookContainer) bookContainer.innerHTML = "<p>Error: Could not load book inventory. Please try again later.</p>";
        }
    }

    // --- Step 4: Run all website functions after data is loaded ---
    await loadInventory();

    // --- Generate Featured Books on Page Load ---
    const bookContainer = document.getElementById("bookContainer");
    if (bookContainer) {
        bookContainer.innerHTML = ''; // Clear any existing content
        for (const book of booksArray) {
            const bookDiv = document.createElement("div");
            bookDiv.classList.add("book");
            bookDiv.innerHTML = `
                <img src="${book.image}" alt="${book.title}">
                <h3>${book.title}</h3>
                <p class="price">₹${book.discount} <span class="old-price">₹${book.mrp}</span></p>
                <a href="book-details.html?id=${book.id}" class="view-details">View Details</a>
            `;
            bookContainer.appendChild(bookDiv);
        }
    }

    // --- Live Search ---
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    if (searchInput && searchResults) {
        searchInput.addEventListener('input', function () {
            const query = this.value.trim().toLowerCase();
            if (query.length < 2) {
                searchResults.style.display = 'none';
                return;
            }
            const filteredBooks = booksArray.filter(b => 
                b.title.toLowerCase().includes(query) || 
                b.author.toLowerCase().includes(query)
            );

            if (filteredBooks.length > 0) {
                searchResults.innerHTML = filteredBooks.map(book => `
                    <a href="book-details.html?id=${book.id}" class="search-result-item">
                        <img src="${book.image}" width="40" style="margin-right: 10px;">
                        <div>
                            <div class="search-result-title">${book.title}</div>
                            <div class="search-result-author">${book.author}</div>
                        </div>
                    </a>`).join('');
            } else {
                searchResults.innerHTML = '<div class="search-no-results">No books found</div>';
            }
            searchResults.style.display = 'block';
        });

         // Hide search results when clicking elsewhere
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target)) {
                searchResults.style.display = 'none';
            }
        });
    }

    // --- Hero Slider, Mobile Nav, and Dropdowns (Your Original Logic) ---
    // (This part remains the same as your working version)
}); 