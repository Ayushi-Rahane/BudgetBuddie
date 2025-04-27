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
    return redirect(url_for('add_expense_page'))


# Delete an expense (DELETE EXPENSE)
@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    conn.commit()
    return redirect(url_for('view_expense_page'))

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
    return redirect(url_for('view_expense_page'))


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
    
#Add expense page rendering
@app.route('/add_expense_page')
def add_expense_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor.execute("SELECT * FROM expenses order by date desc limit 3")
    expenses = cursor.fetchall()    
    return render_template('add_expense.html',expenses=expenses)


#View expense page rendering
@app.route('/view_expense_page')
def view_expense_page():
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

        return render_template('view_expense.html', expenses=expenses)


@app.route('/income_page')
def income_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch all incomes
    cursor.execute("SELECT * FROM income WHERE user_id = %s ORDER BY date DESC LIMIT 3", (session['user_id'],))
    incomes = cursor.fetchall()

    # Fetch income grouped by source for Pie Chart
    cursor.execute("SELECT source, SUM(amount) as total FROM income WHERE user_id = %s GROUP BY source", (session['user_id'],))
    income_sources = cursor.fetchall()

    total_income = sum(row['total'] for row in income_sources)

    # Generate pie chart
    if income_sources:
        labels = [row['source'] for row in income_sources]
        sizes = [row['total'] for row in income_sources]
        create_income_piechart(labels, sizes, total_income)
        chart_available = True
    else:
        chart_available = False

    return render_template('income.html', incomes=incomes, chart_url=chart_available)
#piechart function to show income based on income source
def create_income_piechart(labels, sizes, total_income):
    # Colors (optional: you can customize)
    colors = plt.cm.Paired.colors[:len(labels)]

    # Create a figure for the pie chart
    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=None, 
        autopct='%1.1f%%', 
        startangle=140, 
        colors=colors,
        textprops={'color':"w"}
    )

    # Draw circle for donut
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig.gca().add_artist(centre_circle)

    # Add Total Income in center
    plt.text(0, 0, f'Total\n₹{total_income:.2f}', horizontalalignment='center', verticalalignment='center', fontsize=14, fontweight='bold')

    # Add Legend
    ax.legend(wedges, labels, title="Sources", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

    plt.tight_layout()

    # Save chart to static folder (no GUI)
    plt.savefig('static/piechart_income.png', transparent=True)

    # Close the plot to avoid GUI interference
    plt.close()


@app.route('/add_income', methods=['POST'])
def add_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    amount = request.form['amount']
    date = request.form.get('date')
    if not date:
        date = datetime.today()
    else:
        date = datetime.strptime(date, '%Y-%m-%d')
    source = request.form['source']
    user_id = session['user_id']
    cursor.execute(
        "INSERT INTO income (user_id, amount, source, date) VALUES (%s, %s, %s, %s)",
        (user_id, amount,source, date)
    )
    conn.commit()
    return redirect(url_for('income_page'))



@app.route('/edit_income_page/<int:income_id>')
def edit_income_page(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor.execute("SELECT * FROM income WHERE id = %s", (income_id,))
    income = cursor.fetchone()

    if not income:
        return "Income not found", 404

    return render_template('edit_income.html', income=income)

@app.route('/update_income/<int:income_id>', methods=['POST'])
def update_income(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    amount = request.form['amount']
    source = request.form['source']
    date = request.form['date']
    
    if not date:
        date = datetime.today()
    else:
        date = datetime.strptime(date, '%Y-%m-%d')
    
    cursor.execute(
        "UPDATE income SET amount = %s, source = %s, date = %s WHERE id = %s",
        (amount, source, date, income_id)
    )
    conn.commit()
    return redirect(url_for('income_page'))


@app.route('/delete_income/<int:income_id>', methods=['POST'])
def delete_income(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor.execute("DELETE FROM income WHERE id = %s", (income_id,))
    conn.commit()
    return redirect(url_for('income_page'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, threaded=False)