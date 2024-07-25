import os
from flask import Flask, render_template, request, session, redirect , url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask import jsonify
from functools import wraps

cur_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///"+os.path.join(cur_dir+'/directory',"grocerystore.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
app.app_context().push()

login_manager = LoginManager()
login_manager.init_app(app)

def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user.is_authenticated and current_user.isadmin == 1:
            return func(*args, **kwargs)
        else:
            logout_user()
            return redirect(url_for('login')) 
    return decorated_view

def user_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user.is_authenticated and current_user.isadmin == 0:
            return func(*args, **kwargs)
        else:
            logout_user()
            return redirect(url_for('login'))  
    return decorated_view

class User(UserMixin, db.Model):
    __tablename__ = "User"
    uid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(20), nullable=False)
    isadmin = db.Column(db.Integer, default=0)
    
    def get_id(self):
        return str(self.uid)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Categories(db.Model):
    __tablename__ = "Categories"
    cid = db.Column(db.Integer, autoincrement=True, primary_key=True, nullable=False)
    cname = db.Column(db.String(20), nullable=False)
    products = db.relationship('Products', backref='category', lazy=True)

class Products(db.Model):
    __tablename__ = "Products"
    pid = db.Column(db.Integer, primary_key=True, nullable=False)
    pname = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    quan = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(20))
    cid = db.Column(db.Integer, db.ForeignKey("Categories.cid"))
    mfd = db.Column(db.String(20))
    exp = db.Column(db.String(20))

class Cart(db.Model):
    __tablename__ = "Cart"
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey("User.uid"))
    cid = db.Column(db.Integer, db.ForeignKey("Categories.cid"))
    pid = db.Column(db.Integer, db.ForeignKey("Products.pid"), nullable=False)
    order = db.Column(db.Integer, nullable=False)

@app.route('/')
def index():
    session['user']=None
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form['password']
        check = User.query.all()
        for i in check:
            if username == i.username:
                return render_template('signup.html', text1="This username is already registered!")
        entry = User(username=username, password=password, isadmin=0)
        #session['user']={'id':entry.uid}

        db.session.add(entry)
        db.session.commit()
        db.session.refresh(entry)
        return render_template('login.html', text1="Registered Successfully! Please login.")
        #return (redirect(url_for("userdash")))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session['user']={'id':user.uid}
            login_user(user)

            if user.isadmin == 1:
                return redirect(url_for("admindash"))
            else:
                return redirect(url_for("userdash"))
        else:
            return render_template('login.html', text1="Invalid credentials")

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admindash', methods=['GET', 'POST'])
@login_required
@admin_required
def admindash():
    categories = Categories.query.all()
    return render_template('admindash.html', categories=categories)    

@app.route('/addCategory', methods=['GET', 'POST'])
@app.route('/updateCategory/<int:cid>', methods=['GET', 'POST'])
@login_required
@admin_required
def manageCategory(cid=None):
    category = Categories.query.get(cid) if cid else None

    if request.method == 'POST':
        cat_name = request.form.get('category')

        if cat_name:
            if category:
                category.cname = cat_name
            else:
                new_category = Categories(cname=cat_name)
                db.session.add(new_category)
            db.session.commit()
            return redirect(url_for('admindash'))

    return render_template('addCategory.html', category=category)

@app.route('/deleteCategory/<int:cid>', methods=['POST'])
@login_required
@admin_required
def deleteCategory(cid):
    category = Categories.query.get(cid)
    
    if category:
        for product in category.products:
            db.session.delete(product)
        
        db.session.delete(category)
        db.session.commit()
        
    return redirect(url_for('admindash'))


@app.route('/addProduct/<int:cid>', methods=['GET', 'POST'])
@login_required
@admin_required
def addProduct(cid):
    categories = Categories.query.all()

    if request.method == 'POST':
        product_name = request.form.get('product')
        unit = request.form.get('unit')
        rate_per_unit = int(request.form.get('rate_per_unit'))
        quantity = int(request.form.get('quantity'))
        manufacture_date = request.form.get('manufacture_date')
        m_date = manufacture_date[8:10] + "-" + manufacture_date[5:7] + "-" + manufacture_date[0:4]
        expiry_date = request.form.get('expiry_date')
        e_date = expiry_date[8:10] + "-" + expiry_date[5:7] + "-" + expiry_date[0:4]

        if rate_per_unit<=0:
            return render_template('addProduct.html', text1="Price cannot be 0 or negative!")
        elif quantity<=0:
             return render_template('addProduct.html', text1="Quantity cannot be 0 or negative!")
        else:
            new_product = Products(
            pname=product_name,
            unit=unit,
            price=rate_per_unit,
            quan=quantity,
            mfd=m_date,
            exp=e_date,
            cid=cid )

            db.session.add(new_product)
            db.session.commit()

        return redirect(url_for('admindash'))

    return render_template('addProduct.html', categories=categories)


@app.route('/updateProduct/<int:pid>', methods=['GET', 'POST'])
@login_required
@admin_required
def updateProduct(pid):
    product = Products.query.get(pid)

    if request.method == 'POST':
        product_name = request.form.get('product')
        unit = request.form.get('unit')
        rate_per_unit = int(request.form.get('rate_per_unit'))
        quantity = int(request.form.get('quantity'))
        manufacture_date = request.form.get('manufacture_date')
        m_date = manufacture_date[8:10] + "-" + manufacture_date[5:7] + "-" + manufacture_date[0:4]
        expiry_date = request.form.get('expiry_date')
        e_date = expiry_date[8:10] + "-" + expiry_date[5:7] + "-" + expiry_date[0:4]

        if rate_per_unit<=0:
            return render_template('addProduct.html', text1="Price cannot be 0 or negative!")
        elif quantity<=0:
             return render_template('addProduct.html', text1="Quantity cannot be 0 or negative!")
        
        else:
            product.pname = product_name
            product.unit = unit
            product.price = rate_per_unit
            product.quan = quantity
            product.mfd = m_date
            product.exp = e_date

            db.session.commit()

        return redirect(url_for('admindash'))

    categories = Categories.query.all()
    return render_template('addProduct.html', categories=categories, product=product)

@app.route('/deleteProduct/<int:pid>', methods=['POST'])
@login_required
@admin_required
def deleteProduct(pid):
    product = Products.query.get(pid)
    
    if product:
        db.session.delete(product)
        db.session.commit()
        
    return redirect(url_for('admindash'))

@app.route('/userdash', methods=['GET', 'POST'])
@login_required
@user_required
def userdash():
    categories = Categories.query.all()
    return render_template('userdash.html', categories=categories)

@app.route('/addtoCart/<int:pid>', methods=['POST'])
@login_required
@user_required
def addtoCart(pid):

    categories = Categories.query.all()
    product = Products.query.filter_by(pid=pid).first()
    quantity = request.form.get('quantity')

    text1 = None 
    text1_pid = None  
    
    if int(quantity) > int(product.quan):
        text1 = 'Cannot buy more than available!'
        text1_pid = pid
        return render_template('userdash.html', categories=categories, text1=text1, text1_pid=text1_pid)

    else:
        Products.query.filter_by(pid = pid).update({'quan':Products.quan-int(quantity)})
        c=Cart()
        c.uid=session.get('user')['id']
        c.cid=Products.query.filter_by(pid=pid).first().cid
        c.pid=pid
        c.order=quantity
        db.session.add(c)
        db.session.commit()
        print('complete')
       
        return redirect('/myCart')
    
@app.route('/myCart')
@login_required
@user_required
def mycart():
    cart_items=Cart.query.filter_by(uid=session.get('user')['id']).all()
    uid=session.get('user')['id']
    p=[]
    grand_total = 0
    print(cart_items)
    if cart_items is None:
        return render_template('myCart.html', grand_total=grand_total)
    for i in cart_items:

        product = Products.query.filter_by(pid=i.pid).first()
        category = Categories.query.filter_by(cid=i.cid).first()
        item_total = product.price * i.order

        p.append({'item_id': i.id,
                'pname':Products.query.filter_by(pid=i.pid).first().pname,
                'quan':Cart.query.filter_by(pid=i.pid).first().order,
                'mfd':Products.query.filter_by(pid=i.pid).first().mfd,
                'exp':Products.query.filter_by(pid=i.pid).first().exp,
                'price':Products.query.filter_by(pid=i.pid).first().price,
                'unit':Products.query.filter_by(pid=i.pid).first().unit,
                'category':Categories.query.filter_by(cid=i.cid).first().cname})
        
        grand_total += item_total

    return render_template('myCart.html', cart_items=p, grand_total=grand_total)

@app.route('/removefromCart/<int:item_id>')
@login_required
@user_required
def removefromCart(item_id):
    cart_item = Cart.query.get(item_id)
    if cart_item:
        product = Products.query.filter_by(pid=cart_item.pid).first()
        product.quan += cart_item.order 
        db.session.delete(cart_item)  
        db.session.commit()
    return redirect('/myCart')

@app.route('/search', methods=["POST", "GET"])
@login_required
@user_required
def search():
    if request.method == "POST":
        search_query = request.form.get('search_query', '')
        product_results = Products.query.filter(
            (Products.pname.ilike(f'%{search_query}%')) |
            (Products.price.ilike(f'%{search_query}%')) |
            (Products.mfd.ilike(f'%{search_query}%')) |
            (Products.exp.ilike(f'%{search_query}%'))
        ).all()
        category_results = Categories.query.filter(Categories.cname.ilike(f'%{search_query}%')).all()
        return render_template('searchResults.html', product_results=product_results, category_results=category_results)
    return render_template('searchResults.html')
    
@app.route('/adminSearch', methods=["POST", "GET"])
@login_required
@admin_required
def adminSearch():
    if request.method == "POST":
        search_query = request.form.get('search_query', '')
        product_results = Products.query.filter(
            (Products.pname.ilike(f'%{search_query}%')) |
            (Products.price.ilike(f'%{search_query}%')) |
            (Products.mfd.ilike(f'%{search_query}%')) |
            (Products.exp.ilike(f'%{search_query}%'))
        ).all()
        category_results = Categories.query.filter(Categories.cname.ilike(f'%{search_query}%')).all()
        return render_template('adminSearch.html', product_results=product_results, category_results=category_results)
    return render_template('adminSearch.html')

@app.route('/api/products', methods=['GET'])
def get_all_products():
    products = Products.query.all()
    product_list = []
    for product in products:
        product_data = {
            'pid': product.pid,
            'pname': product.pname,
            'price': product.price,
            'quan': product.quan,
            'unit': product.unit,
            'cid': product.cid,
            'mfd': product.mfd,
            'exp': product.exp
        }
        product_list.append(product_data)
    return jsonify({'products': product_list})

@app.route('/api/products/<int:pid>', methods=['GET'])
def get_product_by_id(pid):
    product = Products.query.get(pid)
    if product:
        product_data = {
            'pid': product.pid,
            'pname': product.pname,
            'price': product.price,
            'quan': product.quan,
            'unit': product.unit,
            'cid': product.cid,
            'mfd': product.mfd,
            'exp': product.exp
        }
        return jsonify(product_data)
    return jsonify({'message': 'Product not found'}), 404

@app.route('/api/categories', methods=['GET'])
def get_all_categories():
    categories = Categories.query.all()
    category_list = []
    for category in categories:
        category_data = {
            'cid': category.cid,
            'cname': category.cname,
        }
        category_list.append(category_data)
    return jsonify({'categories': category_list})

@app.route('/api/categories/<int:cid>', methods=['GET'])
def get_category_by_id(cid):
    category = Categories.query.get(cid)
    if category:
        category_data = {
            'cid': category.cid,
            'cname': category.cname,
        }
        return jsonify(category_data)
    return jsonify({'message': 'Category not found'}), 404

if __name__ == '__main__':
    app.secret_key="rushil"
    app.run(debug=True, host='0.0.0.0')

