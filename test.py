import requests

bookApiKey = "cszJgQV8uqkX9dEmfJQpxg"

def main():
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": bookApiKey, "isbns": '1416949658'})
    data = res.json()
    print(data['books'][0]['average_rating'])
    print(data)


if __name__ == '__main__':
    main()