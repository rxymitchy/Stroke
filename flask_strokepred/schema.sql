DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

from sqlite3 import IntegrityError

try:
    # Attempt to insert the user
    save_user(username, email, password)
except IntegrityError as e:
    # Handle unique constraint violation
    flash('Username or email already exists. Please choose different credentials.', 'error')
    return render_template('register.html')