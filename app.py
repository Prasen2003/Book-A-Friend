import streamlit as st
import pandas as pd
import sqlite3
import random
import urllib.parse
from streamlit.components.v1 import html as st_html

# Establish database connection
conn = sqlite3.connect('book_recommendation_with_ratings.db')
c = conn.cursor()

# Create necessary tables if not exists
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS book_interests (
    user_id INTEGER,
    isbn TEXT,
    rating INTEGER,
    UNIQUE(user_id, isbn),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS reading_status (
    user_id INTEGER,
    isbn TEXT,
    PRIMARY KEY(user_id),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)''')

conn.commit()

# Load book data
df_books = pd.read_csv('data/BX-Books.csv', sep=';', encoding='latin-1')

def calculate_average_rating(isbn):
    # Connect to the database
    conn = sqlite3.connect('book_recommendation_with_ratings.db')
    c = conn.cursor()

    # Query to calculate the sum of ratings for the book
    c.execute("SELECT SUM(rating) FROM book_interests WHERE isbn=?", (isbn,))
    sum_ratings_result = c.fetchone()
    sum_ratings = sum_ratings_result[0] if sum_ratings_result[0] is not None else 0

    # Query to calculate the count of ratings for the book
    c.execute("SELECT COUNT(*) FROM book_interests WHERE isbn=?", (isbn,))
    count_ratings_result = c.fetchone()
    count_ratings = count_ratings_result[0] if count_ratings_result[0] is not None else 0

    # Close the database connection
    conn.close()

    # Calculate the average rating
    if count_ratings == 0:
        return 0  # Return 0 if there are no ratings
    else:
        return sum_ratings / count_ratings  # Return the average rating

# Function to update user's current reading status
def update_reading_status(user_id, isbn):
    c.execute("REPLACE INTO reading_status (user_id, isbn) VALUES (?, ?)", (user_id, isbn))
    conn.commit()

# Function to remove book from user's reading status
def remove_reading_status(user_id):
    c.execute("DELETE FROM reading_status WHERE user_id=?", (user_id,))
    conn.commit()

# Function to get user's current reading status
def get_reading_status(user_id):
    c.execute("SELECT isbn FROM reading_status WHERE user_id=?", (user_id,))
    result = c.fetchone()
    return result[0] if result else None

# Function to display books with images, ratings, and average rating
def display_books(df, ratings=None, allow_rating_adjustment=False, allow_removal=False, user_id=None, allow_add_to_reading_status=True):
    if df.empty:
        st.write("No books to display.")
    else:
        for _, book in df.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.image(book['Image-URL-L'], width=100)
                with col2:
                    # Construct Amazon Kindle search query URL
                    search_query = f"{book['Book-Title']} {book['Book-Author']} Kindle"
                    amazon_kindle_url = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(search_query)}"
                    # Make book title clickable to search on Amazon Kindle
                    book_info = f"**Title**: [{book['Book-Title']}]({amazon_kindle_url})\n"
                    st.markdown(book_info, unsafe_allow_html=True)
                    st.write(f"**Author**: {book['Book-Author']}")
                    st.write(f"**Year**: {book['Year-Of-Publication']}")
                    # Calculate and display average rating
                    average_rating = calculate_average_rating(book['ISBN'])
                    st.write(f"**Average Rating**: {average_rating:.2f}")

                    # Display or adjust rating if available
                    if ratings and book['ISBN'] in ratings:
                        if allow_rating_adjustment:
                            current_rating = ratings[book['ISBN']]
                            new_rating = st.slider(f"Rate '{book['Book-Title']}'", 1, 5, current_rating, key=f"slider_{book['ISBN']}")
                            if new_rating != current_rating:
                                # Update the existing rating in the database instead of inserting a new one
                                c.execute("UPDATE book_interests SET rating=? WHERE user_id=? AND isbn=?", 
                                        (new_rating, user_id, book['ISBN']))
                                conn.commit()
                                st.experimental_rerun()  # Rerun to update the UI
                        else:
                            st.write(f"**Your Rating**: {ratings[book['ISBN']]}")

                    # Add to/remove from current reading status option
                    if allow_add_to_reading_status:
                        is_in_reading_status = get_reading_status(user_id) == book['ISBN']
                        if is_in_reading_status:
                            remove_from_reading_status = st.button("Remove from Reading Status", key=f"remove_reading_status_{book['ISBN']}")
                            if remove_from_reading_status:
                                remove_reading_status(user_id)
                                st.success(f"Removed '{book['Book-Title']}' from your reading status.")
                        else:
                            add_to_reading_status = st.button("Add to Reading Status", key=f"add_reading_status_{book['ISBN']}")
                            if add_to_reading_status:
                                update_reading_status(user_id, book['ISBN'])
                                st.success(f"Added '{book['Book-Title']}' to your reading status.")

                if allow_removal and user_id is not None:
                    with col3:
                        if st.button(f"Remove '{book['Book-Title']}'", key=f"remove_{book['ISBN']}"):
                            # Remove the book from interests
                            c.execute("DELETE FROM book_interests WHERE user_id=? AND isbn=?", (user_id, book['ISBN']))
                            conn.commit()
                            st.success(f"Removed '{book['Book-Title']}' from interests.")
                            st.experimental_rerun()  # Rerun to update the list

                st.write("---")

# Display books in a horizontal scroller with left and right arrows
def display_books_horizontal_scroll(df):
    if df.empty:
        st.write("No books to display.")
    else:
        num_books = len(df)
        # Set background color and text color to match Streamlit's dark theme
        bg_color = "#262730"  # Dark theme background color
        text_color = "#FFFFFF"  # Dark theme text color
        # Create the HTML content for the scrolling cards
        html_content = f"""
<style>
    .scrolling-container {{
        overflow-x: scroll;
        overflow-y: hidden;
        white-space: nowrap;
        padding-bottom: 10px;
        margin-bottom: -10px;
    }}

    .scrolling-card {{
        display: inline-block;
        margin-right: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-radius: 10px;
        overflow: hidden;
        width: 280px; /* Adjusted width */
        background-color: #262730; /* Dark theme background color */
        color: #FFFFFF; /* Dark theme text color */
        font-family: sans-serif;
    }}

    .scrolling-card img {{
        width: auto;
        height: 200px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }}

    .scrolling-card .card-info {{
        padding: 15px;
        border-bottom-left-radius: 10px;
        border-bottom-right-radius: 10px;
        max-height: 200px; /* Maximum height for card body */
        overflow-y: auto; /* Enable scrolling if content exceeds max height */
    }}

    .scrolling-card p {{
        margin-bottom: 5px; /* Add spacing between paragraphs */
    }}

    .scrolling-card strong {{
        font-weight: bold;
    }}

    /* Custom scrollbar styling */
    ::-webkit-scrollbar {{
        width: 8px; /* Width of the scrollbar */
    }}

    ::-webkit-scrollbar-track {{
        background: #262730; /* Track color */
    }}

    ::-webkit-scrollbar-thumb {{
        background-color: darkgreen ; /* Thumb color */
        border-radius: 4px;
        border: 2px solid #262730; /* Thumb border color */
    }}
</style>


        <div class="scrolling-container">
        """
        # Add each book as a card to the HTML content
        for _, book in df.iterrows():
            html_content += f"""
            <div class="scrolling-card">
                <img src="{book['Image-URL-L']}" alt="Book Cover">
                <div class="card-info">
                    <p><strong>Title:</strong><br><span style="font-size: 14px;">{book['Book-Title']}</span></p>
                    <p><strong>Author:</strong> {book['Book-Author']}</p>
                    <p><strong>Year:</strong> {book['Year-Of-Publication']}</p>

                </div>
            </div>
            """
        html_content += "</div>"
        # Render the HTML content
        st_html(html_content, height=450)


# Manage user login and session state
st.sidebar.title("User Account")

# User ID input for login
user_id_input = st.sidebar.text_input("Enter User-ID or Register a New Account")

# Ensure session state persists across re-runs
if "user_logged_in" not in st.session_state:
    st.session_state["user_logged_in"] = False
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

# User login/registration
if st.sidebar.button("Login/Register"):
    if user_id_input.isdigit():
        user_id = int(user_id_input)

        # Check if the user already exists
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = c.fetchone()

        if user:
            st.sidebar.success(f"Logged in as User ID: {user[0]}")
            st.session_state["user_logged_in"] = True
            st.session_state["user_id"] = user[0]
        else:
            # If not, create a new user
            c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            conn.commit()
            st.sidebar.success("Account created. Logged in.")
            st.session_state["user_logged_in"] = True
            st.session_state["user_id"] = user_id
    else:
        st.sidebar.error("User ID must be a numeric value.")

# Ensure session state reflects the current user
if not st.session_state["user_logged_in"]:
    st.write("Please log in or register to use the book recommendation system.")
    st.stop()

if st.session_state["user_logged_in"]:
    user_id = st.session_state["user_id"]

    # Friend search bar
    friend_id_input = st.sidebar.text_input("Enter Friend's User-ID")

    if st.sidebar.button("Find Friend"):
        if friend_id_input.isdigit():
            friend_id = int(friend_id_input)

            # Display user's current reading status book, if any
            current_reading_isbn = get_reading_status(friend_id)
            if current_reading_isbn:
                current_reading_book = df_books[df_books['ISBN'] == current_reading_isbn].iloc[0]
                st.sidebar.subheader("Friend's Current Reading Status")
                st.sidebar.image(current_reading_book['Image-URL-L'], width=100)
                st.sidebar.write(f"**Title**: {current_reading_book['Book-Title']}")
                st.sidebar.write(f"**Author**: {current_reading_book['Book-Author']}")
                st.sidebar.write("---")
            
            # Retrieve friend's interests from the database
            c.execute("SELECT isbn, rating FROM book_interests WHERE user_id=?", (friend_id,))
            friend_interests = {row[0]: row[1] for row in c.fetchall()}

            if friend_interests:
                st.sidebar.subheader(f"Interests of User ID: {friend_id}")
                interests_df = df_books[df_books['ISBN'].isin(list(friend_interests.keys()))]
                with st.sidebar.expander("Friend's Interests"):
                    for _, book in interests_df.iterrows():
                        st.image(book['Image-URL-L'], width=100)
                        st.write(f"**Title**: {book['Book-Title']}")
                        st.write(f"**Author**: {book['Book-Author']}")
                        st.write(f"**Year**: {book['Year-Of-Publication']}")
                        average_rating = calculate_average_rating(book['ISBN'])
                        st.write(f"**Average Rating**: {average_rating:.2f}")
                        st.write("---")
            else:
                st.sidebar.write("Friend has no interests.")
        else:
            st.sidebar.error("Friend's User ID must be a numeric value.")

    # Main content area
    st.title("Book Recommendation System with Adjustable Ratings")

    # Search bar for finding books to add to interests
    search_query = st.sidebar.text_input("Search for a book by title or author")

    # Get the user's current interests and ratings
    c.execute("SELECT isbn, rating FROM book_interests WHERE user_id=?", (user_id,))
    interests = {row[0]: row[1] for row in c.fetchall()}

    # Display search results
    if search_query:
        search_query = search_query.lower()  # Convert to lowercase for case-insensitive matching
        search_results = df_books[
            df_books['Book-Title'].str.lower().str.contains(search_query, na=False) |
            df_books['Book-Author'].str.lower().str.contains(search_query, na=False)
        ]

        if not search_results.empty:
            selected_book_title = st.sidebar.selectbox("Select a book", search_results['Book-Title'].unique())

            if selected_book_title:
                selected_book = search_results[search_results['Book-Title'] == selected_book_title].iloc[0]

                with st.sidebar.container():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.image(selected_book['Image-URL-L'])
                    with col2:
                        st.write(f"**Title**: {selected_book['Book-Title']}")
                        st.write(f"**Author**: {selected_book['Book-Author']}")

                # Add to interests if not already added
                if selected_book['ISBN'] not in interests:
                    add_button = st.sidebar.button("Add to Interests")
                    if add_button:
                        c.execute("INSERT INTO book_interests (user_id, isbn, rating) VALUES (?, ?, 3)", 
                                  (user_id, selected_book['ISBN']))
                        conn.commit()
                        st.sidebar.success("Book added to interests with a default rating of 3.")
                        st.experimental_rerun()  # Rerun to update the UI
        else:
            st.sidebar.write("No search results found.")

    # Display books already added by the user with adjustable ratings and removal option
    st.subheader("Your Book Interests")

    if interests:
        interests_df = df_books[df_books['ISBN'].isin(list(interests.keys()))]
        display_books(interests_df, interests, allow_rating_adjustment=True, allow_removal=True, user_id=user_id)
    else:
        st.write("You have no books marked as interests.")

    # Recommend related books based on multiple authors from user interests
    st.subheader("Recommended Books Based on Your Interests")

    # Collect unique authors and filter based on rating thresholds
    unique_authors = set()
    for isbn, rating in interests.items():
        if rating >= 3:
            book_author = df_books[df_books['ISBN'] == isbn]['Book-Author'].values[0]
            unique_authors.add(book_author)

    # Find related books based on these authors, ensuring each author has books with appropriate ratings
    # Concatenate the recommended books into one DataFrame
    recommended_books = []

    for author in unique_authors:
        # Get all books by this author
        books_by_author = df_books[df_books['Book-Author'] == author]

        # Determine the number of recommendations based on rating criteria
        num_recommendations = 0
        if any(val >= 4 for val in interests.values()):
            num_recommendations = 3
        elif any(val == 3 for val in interests.values()):
            num_recommendations = 2

        # Ensure sample size does not exceed available books
        available_books = len(books_by_author)
        if num_recommendations > available_books:
            num_recommendations = available_books  # Adjust to available books

        if num_recommendations > 0:
            books_to_recommend = books_by_author.sample(min(num_recommendations, 10), random_state=random.randint(0, 100))
            recommended_books.append(books_to_recommend)

    # Concatenate the recommended books into one DataFrame
    recommended_books_df = pd.concat(recommended_books)

    # Ensure recommendations are unique and do not include user's interests
    recommended_books_df = recommended_books_df[~recommended_books_df['ISBN'].isin(list(interests.keys()))]

    # Display recommended books
    if recommended_books_df.empty:
        st.write("No recommended books found.")
    else:
        display_books_horizontal_scroll(recommended_books_df)

    # Display top-rated books in the horizontal scroller
st.subheader("Top Rated Books")

# Calculate average ratings and count of ratings for each book
ratings_query = """
    SELECT isbn, AVG(rating) AS avg_rating, COUNT(*) AS rating_count
    FROM book_interests
    GROUP BY isbn
    HAVING COUNT(*) >= 1
"""
rating_counts = {}
average_ratings = {}
for row in c.execute(ratings_query):
    isbn, avg_rating, rating_count = row
    rating_counts[isbn] = rating_count
    average_ratings[isbn] = avg_rating

df_books['Average Rating'] = df_books['ISBN'].map(average_ratings)
df_books['Rating Count'] = df_books['ISBN'].map(rating_counts)

# Filter out books with fewer ratings (e.g., less than 5)
top_rated_books_df = df_books[df_books['Rating Count'] >= 1]

# Sort by average rating and rating count
top_rated_books_df = top_rated_books_df.sort_values(by=['Average Rating', 'Rating Count'], ascending=False).head(10)

# Display top-rated books in the horizontal scroller
if top_rated_books_df.empty:
    st.write("No top-rated books found.")
else:
    display_books_horizontal_scroll(top_rated_books_df)


# Close the database connection when the script ends
conn.close()