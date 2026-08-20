from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime
import csv
import io
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    cupboard = db.Column(db.String(50), nullable=False)
    shelf = db.Column(db.String(50))
    box = db.Column(db.String(50))
    expiry_date = db.Column(db.String(20))
    notes = db.Column(db.String(200))

    def __repr__(self):
        return f"<Item {self.name} ({self.cupboard})>"

class Chemical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(100))  # new column
    cupboard = db.Column(db.String(50), nullable=False)
    shelf = db.Column(db.String(50))
    box = db.Column(db.String(50))
    quantity = db.Column(db.Integer, nullable=False, default=0)
    volume = db.Column(db.String(50))           # e.g., "500 mL", "2 L"
    expiry_date = db.Column(db.String(20))      # "YYYY-MM-DD" from the date input
    safety_notes = db.Column(db.String(500))

    def __repr__(self):
        return f"<Chemical {self.name} ({self.cupboard} / {self.shelf} / {self.box})>"

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., Protocol, Manual, Report, SOP
    document_type = db.Column(db.String(100))  # e.g., PDF, Word, Excel, Image
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(300), nullable=False)
    tags = db.Column(db.String(300))  # comma-separated tags
    uploaded_by = db.Column(db.String(100))
    
    def __repr__(self):
        return f"<Document {self.title} ({self.category})>"
    

with app.app_context():
    db.create_all()

# ---------- MAIN INDEX (default page) ----------
@app.route('/')
def index():
    # Get search parameters
    search_term = request.args.get('q', '').strip()
    cupboard_filter = request.args.get('cupboard', '').strip()
    
    # Start with base query
    query = Item.query
    
    # Apply search filter if provided
    if search_term:
        query = query.filter(
            or_(
                Item.name.ilike(f'%{search_term}%'),
                Item.cupboard.ilike(f'%{search_term}%'),
                Item.shelf.ilike(f'%{search_term}%'),
                Item.box.ilike(f'%{search_term}%'),
                Item.notes.ilike(f'%{search_term}%')
            )
        )
    
    # Apply cupboard filter if provided
    if cupboard_filter:
        query = query.filter(Item.cupboard == cupboard_filter)
    
    # Execute query
    items = query.order_by(Item.name.asc()).all()
    
    # Get unique cupboards for dropdown
    cupboards = [c[0] for c in db.session.query(Item.cupboard).distinct().all() if c[0]]
    
    return render_template('index.html', 
                         items=items, 
                         search=search_term, 
                         cupboard=cupboard_filter,
                         cupboards=cupboards)

# ---------- CHEMICALS: list ----------
@app.route('/chemicals')
def chemicals():
    search = request.args.get('search', '').strip()
    cupboard = request.args.get('cupboard', '').strip()
    category = request.args.get('category', '').strip()

    query = Chemical.query

    # search across multiple fields
    if search:
        query = query.filter(
            or_(
                Chemical.name.ilike(f"%{search}%"),
                Chemical.cupboard.ilike(f"%{search}%"),
                Chemical.shelf.ilike(f"%{search}%"),
                Chemical.box.ilike(f"%{search}%"),
                Chemical.volume.ilike(f"%{search}%"),
                Chemical.safety_notes.ilike(f"%{search}%"),
                Chemical.category.ilike(f"%{search}%")
            )
        )

    # cupboard filter
    if cupboard:
        query = query.filter(Chemical.cupboard == cupboard)

    # category filter
    if category:
        query = query.filter(Chemical.category == category)

    chems = query.order_by(Chemical.name.asc()).all()

    # send full lists of cupboards & categories for dropdowns
    cupboards = [c[0] for c in db.session.query(Chemical.cupboard).distinct().all()]
    categories = [c[0] for c in db.session.query(Chemical.category).distinct().all() if c[0]]

    return render_template(
        'chemicals.html',
        chemicals=chems,
        search=search,
        cupboard=cupboard,
        category=category,
        cupboards=cupboards,
        categories=categories
    )

@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        new_item = Item(
            name=request.form['name'].strip(),
            quantity=int(request.form['quantity']),
            cupboard=request.form['cupboard'].strip(),
            shelf=request.form.get('shelf', '').strip(),
            box=request.form.get('box', '').strip(),
            expiry_date=request.form.get('expiry_date', '').strip(),
            notes=request.form.get('notes', '').strip()
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_item.html')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form['name'].strip()
        item.quantity = int(request.form['quantity'])
        item.cupboard = request.form['cupboard'].strip()
        item.shelf = request.form.get('shelf', '').strip()
        item.box = request.form.get('box', '').strip()
        item.expiry_date = request.form.get('expiry_date', '').strip()
        item.notes = request.form.get('notes', '').strip()
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit_item.html', item=item)

@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/cupboard/<cupboard_name>')
def cupboard_view(cupboard_name):
    # fetch all items for this cupboard
    items = Item.query.filter_by(cupboard=cupboard_name).order_by(Item.shelf.asc(), Item.name.asc()).all()
    # group by shelf
    grouped = {}
    for it in items:
        key = it.shelf if (it.shelf and it.shelf.strip()) else "— (no shelf)"
        grouped.setdefault(key, []).append(it)
    # sort shelves with natural-ish order when possible
    def shelf_sort_key(s):
        # try to extract integer if shelf is like '1' or 'Shelf 2' etc.
        import re
        m = re.search(r'(\d+)', s)
        return (0, int(m.group(1))) if m else (1, s.lower())
    sorted_shelves = sorted(grouped.keys(), key=shelf_sort_key)
    return render_template('cupboard_view.html', grouped=grouped, shelves=sorted_shelves, cupboard_name=cupboard_name)

@app.route('/export/csv')
def export_csv():
    # Export all items to CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Quantity", "Cupboard", "Shelf", "Box", "Expiry Date", "Notes"])
    for it in Item.query.order_by(Item.name.asc()).all():
        writer.writerow([it.id, it.name, it.quantity, it.cupboard, it.shelf or "", it.box or "", it.expiry_date or "", it.notes or ""])
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    filename = f"lab_inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/csv')

@app.route('/chemicals/cupboard/<cupboard_name>')
def chemicals_cupboard_view(cupboard_name):
    chems = Chemical.query.filter_by(cupboard=cupboard_name).order_by(Chemical.shelf.asc(), Chemical.name.asc()).all()
    grouped = {}
    for c in chems:
        key = c.shelf if (c.shelf and c.shelf.strip()) else "— (no shelf)"
        grouped.setdefault(key, []).append(c)

    def shelf_sort_key(s):
        import re
        m = re.search(r'(\d+)', s)
        return (0, int(m.group(1))) if m else (1, s.lower())

    sorted_shelves = sorted(grouped.keys(), key=shelf_sort_key)
    return render_template('chemicals_cupboard_view.html', grouped=grouped, shelves=sorted_shelves, cupboard_name=cupboard_name)

# ---------- CHEMICALS: add ----------
@app.route('/chemicals/add', methods=['GET', 'POST'])
def add_chemical():
    if request.method == 'POST':
        new = Chemical(
           name=request.form['name'].strip(),
           cupboard=request.form['cupboard'].strip(),
           shelf=request.form.get('shelf', '').strip(),
           box=request.form.get('box', '').strip(),
           quantity=int(request.form.get('quantity', 0)),
           volume=request.form.get('volume', '').strip(),
           expiry_date=request.form.get('expiry_date', '').strip(),
           safety_notes=request.form.get('safety_notes', '').strip(),
           category=request.form.get('category', '').strip()  # new
        )
        db.session.add(new)
        db.session.commit()
        return redirect(url_for('chemicals'))
    return render_template('add_chemical.html')

# ---------- CHEMICALS: edit ----------
@app.route('/chemicals/edit/<int:chem_id>', methods=['GET', 'POST'])
def edit_chemical(chem_id):
    chem = Chemical.query.get_or_404(chem_id)
    if request.method == 'POST':
        chem.name = request.form['name'].strip()
        chem.category = request.form.get('category', '').strip()
        chem.cupboard = request.form['cupboard'].strip()
        chem.shelf = request.form.get('shelf', '').strip()
        chem.box = request.form.get('box', '').strip()
        chem.quantity = int(request.form.get('quantity', 0))
        chem.volume = request.form.get('volume', '').strip()
        chem.expiry_date = request.form.get('expiry_date', '').strip()
        chem.safety_notes = request.form.get('safety_notes', '').strip()
        db.session.commit()
        return redirect(url_for('chemicals'))
    return render_template('edit_chemical.html', chem=chem)

# ---------- CHEMICALS: delete ----------
@app.route('/chemicals/delete/<int:chem_id>')
def delete_chemical(chem_id):
    chem = Chemical.query.get_or_404(chem_id)
    db.session.delete(chem)
    db.session.commit()
    return redirect(url_for('chemicals'))

# ---------- CHEMICALS: export CSV ----------
@app.route('/export/chemicals/csv')
def export_chemicals_csv():
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID", "Name", "Cupboard", "Shelf", "Box", "Quantity", "Volume", "Expiry Date", "Safety Notes"])
    for c in Chemical.query.order_by(Chemical.name.asc()).all():
        w.writerow([c.id, c.name, c.cupboard, c.shelf or "", c.box or "", c.quantity, c.volume or "", c.expiry_date or "", c.safety_notes or ""])
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    filename = f"chemicals_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/csv')

# ---------- HOME (navigation page) ----------
@app.route('/home')
def home():
    # Get counts for stats
    total_items = Item.query.count()
    total_chemicals = Chemical.query.count()
    
    # Get recent items (last 5 added)
    recent_items = Item.query.order_by(Item.id.desc()).limit(5).all()
    recent_chemicals = Chemical.query.order_by(Chemical.id.desc()).limit(5).all()
    
    # For now, set these to 0 - you can implement later
    expiring_soon = 0
    low_stock = 0
    
    return render_template('home.html',
                         total_items=total_items,
                         total_chemicals=total_chemicals,
                         expiring_soon=expiring_soon,
                         low_stock=low_stock,
                         recent_items=recent_items,
                         recent_chemicals=recent_chemicals)

# ---------- GLOBAL SEARCH (searches both items and chemicals) ----------
@app.route('/search')
def global_search():
    search_term = request.args.get('q', '').strip()
    
    if not search_term:
        return redirect(url_for('home'))
    
    # Search Items
    items = Item.query.filter(
        or_(
            Item.name.ilike(f'%{search_term}%'),
            Item.cupboard.ilike(f'%{search_term}%'),
            Item.shelf.ilike(f'%{search_term}%'),
            Item.box.ilike(f'%{search_term}%'),
            Item.notes.ilike(f'%{search_term}%')
        )
    ).order_by(Item.name.asc()).all()
    
    # Search Chemicals
    chemicals = Chemical.query.filter(
        or_(
            Chemical.name.ilike(f'%{search_term}%'),
            Chemical.cupboard.ilike(f'%{search_term}%'),
            Chemical.shelf.ilike(f'%{search_term}%'),
            Chemical.box.ilike(f'%{search_term}%'),
            Chemical.volume.ilike(f'%{search_term}%'),
            Chemical.safety_notes.ilike(f'%{search_term}%'),
            Chemical.category.ilike(f'%{search_term}%')
        )
    ).order_by(Chemical.name.asc()).all()
    
    return render_template('search_results.html',
                         search_term=search_term,
                         items=items,
                         chemicals=chemicals)

import os
from werkzeug.utils import secure_filename

# Configure upload settings (add these after app configuration)
app.config['UPLOAD_FOLDER'] = 'uploads/documents'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ---------- DOCUMENTS: list ----------
@app.route('/documents')
def documents():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    doc_type = request.args.get('type', '').strip()
    tag = request.args.get('tag', '').strip()
    
    query = Document.query
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Document.title.ilike(f'%{search}%'),
                Document.description.ilike(f'%{search}%'),
                Document.tags.ilike(f'%{search}%')
            )
        )
    
    if category:
        query = query.filter(Document.category == category)
    
    if doc_type:
        query = query.filter(Document.document_type == doc_type)
    
    if tag:
        query = query.filter(Document.tags.ilike(f'%{tag}%'))
    
    docs = query.order_by(Document.upload_date.desc()).all()
    
    # Get unique values for filters
    categories = [c[0] for c in db.session.query(Document.category).distinct().all() if c[0]]
    types = [t[0] for t in db.session.query(Document.document_type).distinct().all() if t[0]]
    all_tags = []
    for tag_str in db.session.query(Document.tags).distinct().all():
        if tag_str[0]:
            all_tags.extend([t.strip() for t in tag_str[0].split(',')])
    tags = list(set(all_tags))  # Remove duplicates
    
    return render_template('documents.html',
                         documents=docs,
                         search=search,
                         category=category,
                         doc_type=doc_type,
                         tag=tag,
                         categories=categories,
                         types=types,
                         tags=tags)

# ---------- DOCUMENTS: upload ----------
@app.route('/documents/upload', methods=['GET', 'POST'])
def upload_document():
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Secure filename and create unique path
            filename = secure_filename(file.filename)
            unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Create document record
            new_doc = Document(
                title=request.form['title'].strip(),
                description=request.form.get('description', '').strip(),
                category=request.form.get('category', '').strip(),
                document_type=filename.rsplit('.', 1)[1].lower(),
                file_path=file_path,
                tags=request.form.get('tags', '').strip(),
                uploaded_by=request.form.get('uploaded_by', 'Admin').strip()
            )
            
            db.session.add(new_doc)
            db.session.commit()
            
            return redirect(url_for('documents'))
    
    return render_template('upload_document.html')

# ---------- DOCUMENTS: download ----------
@app.route('/documents/download/<int:doc_id>')
def download_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    return send_file(doc.file_path, as_attachment=True)

# ---------- DOCUMENTS: view ----------
@app.route('/documents/view/<int:doc_id>')
def view_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    return render_template('view_document.html', document=doc)

# ---------- DOCUMENTS: delete ----------
@app.route('/documents/delete/<int:doc_id>')
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    
    # Delete file from filesystem
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    
    db.session.delete(doc)
    db.session.commit()
    
    return redirect(url_for('documents'))

if __name__ == '__main__':
    # Bind to all interfaces so other PCs on the same LAN can access if needed
    app.run(host='0.0.0.0', port=5000, debug=True)
