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
    category = db.Column(db.String(50))
    cupboard = db.Column(db.String(50), nullable=False)
    shelf = db.Column(db.String(50))
    box = db.Column(db.String(50))
    quantity = db.Column(db.Integer, nullable=False, default=0)
    volume = db.Column(db.String(50))           # e.g., "500 mL", "2 L"
    expiry_date = db.Column(db.String(20))      # "YYYY-MM-DD" from the date input
    safety_notes = db.Column(db.String(500))

    def __repr__(self):
        return f"<Chemical {self.name} ({self.cupboard} / {self.shelf} / {self.box})>"
    

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    search = request.args.get('q', '').strip()
    cupboard = request.args.get('cupboard', '').strip()

    query = Item.query
    if search:
        query = query.filter(
            or_(
                Item.name.contains(search),
                Item.cupboard.contains(search),
                Item.shelf.contains(search),
                Item.box.contains(search),
                Item.notes.contains(search)
            )
        )
    if cupboard:
        query = query.filter(Item.cupboard == cupboard)

    items = query.order_by(Item.name.asc()).all()
    return render_template('index.html', items=items)


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

# ---------- HOME (navigation page) ----------
@app.route('/home')
def home():
    return render_template('home.html')

# ---------- CHEMICALS: list ----------
@app.route('/chemicals')
def chemicals():
    search = request.args.get('search', '').strip()
    query = Chemical.query
    if search:
        query = query.filter(
            or_(
                Chemical.name.contains(search),
                Chemical.cupboard.contains(search),
                Chemical.shelf.contains(search),
                Chemical.box.contains(search),
                Chemical.category.contains(search),
                Chemical.volume.contains(search),
                Chemical.safety_notes.contains(search)
            )
        )
    chems = query.order_by(Chemical.name.asc()).all()
    return render_template('chemicals.html', chemicals=chems, search=search)

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
            category=request.form.get('category', '').strip(),
            safety_notes=request.form.get('safety_notes', '').strip(),
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
        chem.category = request.form['category'].strip()
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
    import csv, io
    from datetime import datetime
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID", "Name", "Category",  "Cupboard", "Shelf", "Box", "Quantity", "Volume", "Expiry Date", "Safety Notes"])
    for c in Chemical.query.order_by(Chemical.name.asc()).all():
        w.writerow([c.id, c.name, c.cupboard, c.shelf or "", c.box or "", c.quantity, c.volume or "", c.expiry_date or "", c.safety_notes or ""])
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    filename = f"chemicals_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/csv')


if __name__ == '__main__':
    # Bind to all interfaces so other PCs on the same LAN can access if needed
    app.run(host='0.0.0.0', port=5000, debug=True)
