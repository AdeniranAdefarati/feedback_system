from app import db

class User(db.Model):
    __tablename__ = 'users'  # table name in the database
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), default="user")  # 'user' or 'admin'

    def __repr__(self):
        return f'<User {self.name}>'
