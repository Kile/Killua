# Set up the mongo db by creating the database and collections
use Killua --host localhost:27017
db.createCollection("api-stats")

# Done, close the connection
exit