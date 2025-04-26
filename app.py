from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta 
import matplotlib.pyplot as plt
load_dotenv() # Load environment variables from .env file



conn = mysql.connector.connect(
    host="localhost",        
    port=3307,               
    user="root",
    password="root",
    database="budgetbuddie"
)

cursor = conn.cursor(dictionary=True)

app = Flask(__name__)

#app.secret_key = os.getenv('SECRET_KEY')
app.secret_key = '8c0f560fe793bc1ca1899625700c6c0b'


# Function to get budget suggestions based on last month's expenses
def get_budget_suggestions(user_id):
    today = datetime.today() # Get today's date
    first_day_this_month = today.replace(day=1) # Get the first day of the current month

    # Step 1: Get Custom Budgets
    cursor.execute("""
        SELECT category, amount FROM budgets
        WHERE user_id = %s AND month = %s
    """, (user_id, first_day_this_month))
    custom_budgets = {row['category']: row['amount'] for row in cursor.fetchall()} 

    # Step 2: Calculate Last Month's Expenses
    last_month = (first_day_this_month - timedelta(days=1)).replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)

    cursor.execute("""
        SELECT category, SUM(amount) as total FROM expenses
        WHERE user_id = %s AND date BETWEEN %s AND %s
        GROUP BY category
    """, (user_id, last_month, last_day_last_month))
    rows = cursor.fetchall()

    # Step 3: Suggest 90% of last month’s total (or use custom if exists)
    suggestions = {}
    for row in rows:
        category = row['category']
        if category in custom_budgets:
            suggestions[category] = custom_budgets[category]
        else:
            suggestions[category] = round(row['total'] * 0.9)
    
    return suggestions


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form['email']
        password = request.form['password']
        # Check if the user exists in the database
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            # Verify the password
            if check_password_hash(user['password'], password):
                # Password is correct, redirect to the home page
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('home'))
        
        else:
            # User not found
            return "Invalid email or password. Please try again."
            
        
    
    return render_template('login.html')


# Add a new expense (ADD EXPENSE)
@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    title = request.form['title']
    category = request.form['category']
    amount = request.form['amount']
    date = request.form.get('date')
    if not date:
        date = datetime.today()
    else:
        date = datetime.strptime(date, '%Y-%m-%d')

    user_id = session['user_id']  # Assuming the user is logged in

    cursor.execute(
        "INSERT INTO expenses (user_id, title, category, amount, date) VALUES (%s, %s, %s, %s, %s)",
        (user_id, title, category, amount, date)
    )
    conn.commit()
    return redirect(url_for('home'))


# Delete an expense (DELETE EXPENSE)
@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    conn.commit()
    return redirect(url_for('home'))

#Show the Edit form
@app.route('/edit_expense/<int:expense_id>', methods=['GET'])
def edit_expense(expense_id):
    cursor.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
    expense = cursor.fetchone()
    return render_template('edit_expense.html', expense=expense)

#Show the Update form
@app.route('/update_expense/<int:expense_id>', methods=['POST'])
def update_expense(expense_id):
    title = request.form['title']
    category = request.form['category']
    amount = request.form['amount']

    cursor.execute(
        "UPDATE expenses SET title = %s, category = %s, amount = %s WHERE id = %s",
        (title, category, amount, expense_id)
    )
    conn.commit()
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Check if the passwords match
        if password != confirm_password:
            return "Passwords do not match. Please try again."
        
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        # Check if the email already exists in the database
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            return "Email already registered. Please login or use a different email."
        
        # Insert the new user into the database
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        
        return render_template('login.html')
    
    return render_template('register.html')


@app.route('/')
def home():
    if 'user_id' in session:
        # User is logged in, show the home page
        
        user_id = session['user_id']
        search_query = request.args.get('query')
        amount = request.args.get('amount')
        date = request.args.get('date')
        # Fetch expenses from the database
        sql = "SELECT id,title, category, amount, date FROM expenses WHERE user_id = %s"
        params = [user_id]

        if search_query:
            sql +=" AND (title LIKE %s OR category LIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if amount:
            sql += " AND amount = %s"
            params.append(amount)
        
        if date:
            sql += " AND DATE(date) = %s"
            params.append(date)
        
        cursor.execute(sql, tuple(params))
        expenses = cursor.fetchall()

        total = sum(exp['amount'] for exp in expenses)       
        

        return render_template('index.html', expenses=expenses, total=total,)
    
    else:
        # User is not logged in, redirect to the login page
        return redirect(url_for('login'))
    

if __name__ == '__main__':
    app.run(debug=True)