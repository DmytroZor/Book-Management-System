# Book Management System API

REST API for managing  of books.  

## Functional Overview

- **Create Book**   add a new book to the library.  
- **List Books**   retrieve a list of all books.
- **Update Book**   modify information of an existing book.  
- **Delete Book**   remove a book from the library.  
- **Import Books**   upload books in JSON or CSV format.  
- **Export Books**   download books in JSON or CSV format.
 
###
**Book object fields:**
- `id`  unique identifier (integer)  
- `title`  book title (string)  
- `author`  book author (string)