from sqlalchemy import Text
from sqlalchemy.dialects import mysql

# MySQL TEXT holds only 64 KB; a dense page or a long table can exceed that.
# MEDIUMTEXT holds 16 MB. Other databases (SQLite in tests) just use TEXT.
LongText = Text().with_variant(mysql.MEDIUMTEXT(), "mysql")
