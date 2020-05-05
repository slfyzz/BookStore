import os
import requests
from flask import Flask, session,render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

uri = "postgres://ttwyfzdrvfccum:07324fe26aa9980f76fffcc944254a5f88d13f5124e4298fe3e4c31ee3ba1ce2@ec2-54-247-103-43.eu-west-1.compute.amazonaws.com:5432/dfaiijbmnep09b"
bookApiKey = "cszJgQV8uqkX9dEmfJQpxg"

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(uri)
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if not authorize():
        return render_template('Welcome.html', log=False)
    else:
        return render_template('Welcome.html', log=True, user_name=session['user_name'].capitalize())
    


@app.route("/redirect/<string:oper>")
def access(oper):
    if (oper == 'login' or oper == 'signup') and not authorize():
        return render_template('login.html', log=False, oper=oper, error=False)
    elif oper == 'logout' and authorize():
        session.pop('user_id')
        return index()
    else:
        return render_template('notification.html', error='Access denied', message='Sorry, you have no right to be in that page')

@app.route("/signup", methods=["POST"])
def signup():
    userName = request.form.get('name')
    password = request.form.get('password')
    if userName == "" or password == "":
        return render_template('login.html', log=False, oper="signup", error=True, message='fields can not be empty !!')
    
    if db.execute("SELECT * FROM users WHERE name = :name", {"name" : userName}).rowcount != 0:
        return render_template('login.html', log=False, oper="signup", error=True, message='userName is not available')
    
    db.execute("INSERT INTO users (name, password) VALUES(:user, :password)", {"user":userName, "password": password})
    db.commit()
    session['user_id'] = db.execute("SELECT id FROM users WHERE name=:name", {"name":userName}).fetchone().id
    session['user_name'] = userName
    return index()
        
@app.route("/login", methods=["POST"])
def login():
    userName = request.form.get('name')
    password = request.form.get('password')
    if userName == "" or password == "":
        return render_template('login.html', log=False, oper="login", error=True, message='fields can not be empty !!')
    
    user = db.execute("SELECT * FROM users WHERE name = :name AND password = :pass", {"name" : userName, "pass" : password}).fetchone()
    
    if user is None:
        return render_template('login.html', log=False, oper="login", error=True, message='something wrong with userName or password, Try again!')
    
    session['user_id'] = user.id
    session['user_name'] = userName
    return index()
        
@app.route("/search", methods=["POST"])
def search():
    if not authorize():
        return index()
    
    title = request.form.get('title')
    isbn = request.form.get('isbn')
    author = request.form.get('author')
    if title == "" and author == "" and isbn == "":
        return render_template('notification.html', error='Not Found', message='We can\'t find book with those informations, Try again'), 404
    books = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE LOWER(:title) AND isbn LIKE :isbn AND LOWER(author) LIKE LOWER(:author)",
                       {"title" : '%' + title + '%' , "isbn" : '%' + isbn + '%', "author" : '%' + author + '%'}).fetchall()
    
    return render_template('results.html', books=books, log=True, user_name=session['user_name'].capitalize())

@app.route("/quickSearch", methods=["POST"])
def quickSearch():
    if not authorize():
        return index()
    
    search = request.form.get('search')
    if search == "":
       return render_template('notification.html', error='Not Found', message='We can\'t find book with those informations, Try again'), 404
   
    books = db.execute("SELECT * FROM books WHERE LOWER(title) LIKE LOWER(:title) OR isbn LIKE :isbn OR LOWER(author) LIKE LOWER(:author)",
                       {"title" : '%' + search + '%' , "isbn" : '%' + search + '%', "author" : '%' + search + '%'}).fetchall()   
    
    return render_template('results.html', books=books, log=True, user_name=session['user_name'].capitalize())

    
    
@app.route('/book/<string:isbn>', methods=["POST", "GET"])
def book(isbn):
    
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn" : isbn}).fetchone()
    if book is None or not authorize():
        return render_template('notification.html', error='Not Found', message='We can\'t find book with those informations, Try again'), 404
    
    if request.method == 'POST':
        comment = request.form.get('comment')
        rate = int(request.form.get('rate')) + 1
        if rate > 5 or rate < 0:
            return "SHIT"
        else:
            db.execute("INSERT INTO ratings (user_id, book_id, rate, comment) VALUES (:uId, :uB, :rate, :comment)",
                       {"uId": session['user_id'], 'uB': book.id, 'rate' : rate, 'comment': comment})
            db.commit()
                
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": bookApiKey, "isbns": isbn})
    
    
    if res.status_code != 200:
        return render_template('notification.html', error='Error', message='Something wrong happened'), res.status_code

    
    reviewSubmission, data, ratings  = updateJson(res, book)
        
    return render_template('book.html', data=data, comments=ratings, book=book, revSubmit=reviewSubmission, log=True, user_name=session['user_name'].capitalize())
    
def authorize():
    return not (session.get('user_id') is None) 


@app.route('/api/<string:isbn>')
def api(isbn):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn" : isbn}).fetchone()
    if book is None:
        return jsonify({'Error' : 'Not found'}) , 404
    
   
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": bookApiKey, "isbns": isbn})    
    
    if res.status_code != 200:
        return jsonify({'Error' : 'internal Error happened'}), 408
    
    voi , data, ratings = updateJson(res, book)
    return jsonify({
        'title' : book.title,
        'author' : book.author,
        'year' : book.year,
        'isbn' : book.isbn,
        'review_count' : data['work_reviews_count'],
        'ratings_count' : data['work_ratings_count'],
        'average_rating' : data['average_rating']
    })
    
    
    
def updateJson(res, book):
    ratings = db.execute("SELECT name, rate, comment, book_id  FROM ratings JOIN users ON users.id = ratings.user_id WHERE book_id=:id",{"id":book.id}).fetchall()    
    exdata = res.json()
    data = exdata['books'][0]
    avgLocalRates = 0
    reviewSubmission = True
    numOfReviews = 0
    for rate in ratings:
        avgLocalRates += rate.rate
        if rate.name == session['user_name']:
            reviewSubmission = False
        if rate.comment != '':
            numOfReviews += 1
    
    data['average_rating'] = round((float(data['average_rating']) * float(data['work_reviews_count']) + avgLocalRates) / (len(ratings) +  float(data['work_reviews_count'])), 2)
    data['work_ratings_count'] += len(ratings)
    data['work_reviews_count'] += numOfReviews
    return reviewSubmission , data , ratings 
     