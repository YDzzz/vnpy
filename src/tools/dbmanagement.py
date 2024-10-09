import pymysql.cursors
from src.tools.property import Property


class DBManager:

    def __init__(self, database_name: str):
        # Connect to the database
        self.sql_element_num = None
        self.insert_sql = None
        self.connection = pymysql.connect(host=Property.get_property("DB_HOST"),
                                          user=Property.get_property("DB_USER"),
                                          password=Property.get_property("DB_PASSWORD"),
                                          database=database_name,
                                          cursorclass=pymysql.cursors.DictCursor)

    def set_insert_sql(self, insert_sql: str):
        self.insert_sql = insert_sql

        self.sql_element_num = (insert_sql.count("%s")
                                + insert_sql.count("%f")
                                + insert_sql.count("%d"))

    def insert(self, *args):
        if self.sql_element_num != len(args):
            return False
        with self.connection.cursor() as cursor:
            cursor.execute(self.insert_sql, args)
        return True

    def commit(self):
        self.connection.commit()


if __name__ == '__main__':
    db_manager = DBManager("stocks")
    db_manager.set_insert_sql("INSERT INTO `inform` (`symbol`, `name`) VALUES (%s, %s)")