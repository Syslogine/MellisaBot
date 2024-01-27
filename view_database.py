import sqlite3

def delete_database():
    # Code to delete the content of the database
    conn = sqlite3.connect('web_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM web_pages")
    conn.commit()

def view_database():
    # Code to view the content of the database
    conn = sqlite3.connect('web_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM web_pages")
    rows = c.fetchall()
    for row in rows:
        print(row)
    conn.close()

def main():
    command = input("Enter a command (delete/view): ")
    
    if command == "delete":
        delete_database()
    elif command == "view":
        view_database()
    else:
        print("Invalid command")

if __name__ == "__main__":
    main()
