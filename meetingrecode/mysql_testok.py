import pymysql

# 連結 SQL
connect_db = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='',  # 新版建议用 password 而不是 passwd
    charset='utf8',
    database='yilsystem'
)

with connect_db.cursor() as cursor:
    sql = """
    CREATE TABLE IF NOT EXISTS Member(
        ID int NOT NULL AUTO_INCREMENT PRIMARY KEY,
        Name varchar(20),
        Height int(6),
        Weight int(6)
    );
    """
    
    # 執行 SQL 指令
    cursor.execute(sql)
    
    # 提交至 SQL
    connect_db.commit()

# 關閉 SQL 連線
connect_db.close()
