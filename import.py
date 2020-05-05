import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

uri = "postgres://ttwyfzdrvfccum:07324fe26aa9980f76fffcc944254a5f88d13f5124e4298fe3e4c31ee3ba1ce2@ec2-54-247-103-43.eu-west-1.compute.amazonaws.com:5432/dfaiijbmnep09b"

engine = create_engine(uri)
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open('C:\\Users\\3arrows\\Desktop\\CSW\\project1\\books.csv')
    reader = csv.reader(f)
    next(reader, None)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)", 
                   {"isbn" : isbn, "title" : title, "author" : author, "year" : year})
        print(f"{title} is added")
        
    db.commit()
if __name__ == "__main__":
    main()